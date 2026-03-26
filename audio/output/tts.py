#coding=utf-8

'''
requires Python 3.6 or later

pip install asyncio
pip install websockets

'''

import asyncio
import websockets
import uuid
import json
import gzip
import copy
import logging
import os
import yaml
import requests

logger = logging.getLogger(__name__)

def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "settings.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using empty config")
        return {}

_config = _load_config()

MESSAGE_TYPES = {11: "audio-only server response", 12: "frontend server response", 15: "error message from server"}
MESSAGE_TYPE_SPECIFIC_FLAGS = {0: "no sequence number", 1: "sequence number > 0",
                               2: "last message from server (seq < 0)", 3: "sequence number < 0"}
MESSAGE_SERIALIZATION_METHODS = {0: "no serialization", 1: "JSON", 15: "custom type"}
MESSAGE_COMPRESSIONS = {0: "no compression", 1: "gzip", 15: "custom compression method"}

default_header = bytearray(b'\x11\x10\x11\x00')

def _get_request_template(appid: str, cluster: str, voice_type: str) -> dict:
    return {
        "app": {
            "appid": appid,
            "token": "access_token",
            "cluster": cluster
        },
        "user": {
            "uid": "388808087185088"
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": "xxx",
            "text": "",
            "text_type": "plain",
            "operation": "xxx"
        }
    }

class TTSClient:
    def __init__(self):
        tts_config = _config.get("tts", {})
        self.mode = tts_config.get("mode", "server")
        
        if self.mode == "server":
            server_config = tts_config.get("server", {})
            self.appid = server_config.get("appid", "")
            self.token = server_config.get("token", "")
            self.cluster = server_config.get("cluster", "")
            self.voice_type = server_config.get("voice_type", "")
            self.api_url = server_config.get("url", "")
            self.header = {"Authorization": f"Bearer; {self.token}"}
        else:
            local_config = tts_config.get("local", {})
            self.base_url = local_config.get("base_url", "http://127.0.0.1:5000")
            self.character = local_config.get("character", "fufuvoice")
            self.emotion = local_config.get("emotion", "default")
            self.language = local_config.get("language", "多语种混合")

    async def _synthesize_async(self, text: str, output_path: str, voice_type: str = None):
        if self.mode == "server":
            return await self._synthesize_server(text, output_path, voice_type)
        else:
            return await self._synthesize_local(text, output_path)

    async def _synthesize_server(self, text: str, output_path: str, voice_type: str = None):
        voice = voice_type or self.voice_type
        request_json_template = _get_request_template(self.appid, self.cluster, voice)
        
        submit_request_json = copy.deepcopy(request_json_template)
        submit_request_json["app"]["token"] = self.token
        submit_request_json["request"]["reqid"] = str(uuid.uuid4())
        submit_request_json["request"]["text"] = text
        submit_request_json["request"]["operation"] = "submit"
        
        payload_bytes = str.encode(json.dumps(submit_request_json))
        payload_bytes = gzip.compress(payload_bytes)
        full_client_request = bytearray(default_header)
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        full_client_request.extend(payload_bytes)
        
        try:
            async with websockets.connect(self.api_url, extra_headers=self.header, ping_interval=None) as ws:
                await ws.send(full_client_request)
                
                with open(output_path, "wb") as file_to_save:
                    while True:
                        res = await ws.recv()
                        done = self._parse_response(res, file_to_save)
                        if done:
                            break
                return output_path
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise

    async def _synthesize_local(self, text: str, output_path: str):
        import aiohttp
        data = {
            "cha_name": self.character,
            "text": text,
            "character_emotion": self.emotion,
            "text_language": self.language
        }
        
        logger.info(f"Local TTS request: {self.base_url}/tts with data: {data}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.base_url}/tts", json=data) as response:
                    logger.info(f"Local TTS response status: {response.status}")
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"Local TTS audio data size: {len(audio_data)} bytes")
                        
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                        logger.info(f"Local TTS saved to: {output_path}")
                        return output_path
                    else:
                        error_text = await response.text()
                        logger.error(f"Local TTS error: {error_text}")
                        raise Exception(f"TTS request failed with status {response.status}")
        except Exception as e:
            logger.error(f"Local TTS request failed: {e}")
            raise

    def _parse_response(self, res, file):
        protocol_version = res[0] >> 4
        header_size = res[0] & 0x0f
        message_type = res[1] >> 4
        message_type_specific_flags = res[1] & 0x0f
        serialization_method = res[2] >> 4
        message_compression = res[2] & 0x0f
        reserved = res[3]
        header_extensions = res[4:header_size*4]
        payload = res[header_size*4:]
        
        if message_type == 0xb:
            if message_type_specific_flags == 0:
                return False
            else:
                sequence_number = int.from_bytes(payload[:4], "big", signed=True)
                payload_size = int.from_bytes(payload[4:8], "big", signed=False)
                payload = payload[8:]
                
            file.write(payload)
            if sequence_number < 0:
                return True
            else:
                return False
        elif message_type == 0xf:
            code = int.from_bytes(payload[:4], "big", signed=False)
            msg_size = int.from_bytes(payload[4:8], "big", signed=False)
            error_msg = payload[8:]
            if message_compression == 1:
                error_msg = gzip.decompress(error_msg)
            error_msg = str(error_msg, "utf-8")
            logger.error(f"Error message code: {code}")
            logger.error(f"Error message: {error_msg}")
            return True
        elif message_type == 0xc:
            msg_size = int.from_bytes(payload[:4], "big", signed=False)
            payload = payload[4:]
            if message_compression == 1:
                payload = gzip.decompress(payload)
            return False
        else:
            return True

    def synthesize(self, text: str, output_path: str = "output.mp3", voice_type: str = None) -> str:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._synthesize_async(text, output_path, voice_type))
        finally:
            loop.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    client = TTSClient()
    client.synthesize("你好，我是你的语音助手。", "test_tts.mp3")
