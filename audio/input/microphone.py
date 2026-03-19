import speech_recognition as sr
import logging
import pydub
from io import BytesIO
from functools import lru_cache
import os

# Configure logging (ensure this is configured in your main application as well)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@lru_cache(maxsize=None)
def get_recognizer():
    """
    Return a cached speech recognizer instance
    """
    return sr.Recognizer()

def record_audio(file_path, timeout=10, phrase_time_limit=None, retries=3, energy_threshold=2000, 
                 pause_threshold=1, phrase_threshold=0.1, dynamic_energy_threshold=True, 
                 calibration_duration=1):
    """
    Record audio from the microphone and save it as an audio file (MP3 or WAV).
    
    Args:
    file_path (str): The path to save the recorded audio file.
    timeout (int): Maximum time to wait for a phrase to start (in seconds).
    phrase_time_limit (int): Maximum time for the phrase to be recorded (in seconds).
    retries (int): Number of retries if recording fails.
    energy_threshold (int): Energy threshold for considering whether a given chunk of audio is speech or not.
    pause_threshold (float): How much silence the recognizer interprets as the end of a phrase (in seconds).
    phrase_threshold (float): Minimum length of a phrase to consider for recording (in seconds).
    dynamic_energy_threshold (bool): Whether to enable dynamic energy threshold adjustment.
    calibration_duration (float): Duration of the ambient noise calibration (in seconds).
    """
    recognizer = get_recognizer()
    recognizer.energy_threshold = energy_threshold
    recognizer.pause_threshold = pause_threshold
    recognizer.phrase_threshold = phrase_threshold
    recognizer.dynamic_energy_threshold = dynamic_energy_threshold
    
    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    for attempt in range(retries):
        try:
            with sr.Microphone() as source:
                logging.info(f"Calibrating for ambient noise... (Attempt {attempt + 1}/{retries})")
                if dynamic_energy_threshold:
                    recognizer.adjust_for_ambient_noise(source, duration=calibration_duration)
                
                logging.info("Recording started. Speak now...")
                # Listen for the first phrase and extract it into audio data
                audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                logging.info("Recording complete")

                # Save audio data
                if file_path.lower().endswith('.mp3'):
                    # Convert the recorded audio data to an MP3 file
                    wav_data = audio_data.get_wav_data()
                    audio_segment = pydub.AudioSegment.from_wav(BytesIO(wav_data))
                    audio_segment.export(file_path, format="mp3", bitrate="128k", parameters=["-ar", "22050", "-ac", "1"])
                else:
                    # Save as WAV directly
                    with open(file_path, "wb") as f:
                        f.write(audio_data.get_wav_data())
                
                return
        except sr.WaitTimeoutError:
            logging.warning(f"Listening timed out, retrying... ({attempt + 1}/{retries})")
        except Exception as e:
            logging.error(f"Failed to record audio: {e}")
            if attempt == retries - 1:
                raise
        
    logging.error("Recording failed after all retries")
    raise Exception("Recording failed after all retries")

if __name__ == "__main__":
    # Test the recording
    logging.basicConfig(level=logging.INFO)
    try:
        test_file = "test_recording.mp3"
        print(f"Recording to {test_file}...")
        record_audio(test_file, timeout=5, phrase_time_limit=5)
        print(f"Recording saved to {test_file}")
    except Exception as e:
        print(f"Test failed: {e}")
