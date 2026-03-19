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

logger = logging.getLogger(__name__)

MESSAGE_TYPES = {11: "audio-only server response", 12: "frontend server response", 15: "error message from server"}
MESSAGE_TYPE_SPECIFIC_FLAGS = {0: "no sequence number", 1: "sequence number > 0",
                               2: "last message from server (seq < 0)", 3: "sequence number < 0"}
MESSAGE_SERIALIZATION_METHODS = {0: "no serialization", 1: "JSON", 15: "custom type"}
MESSAGE_COMPRESSIONS = {0: "no compression", 1: "gzip", 15: "custom compression method"}

# 默认配置
DEFAULT_APPID = "1972357714"
DEFAULT_TOKEN = "jhG-6VnZk0h4EAhD9CekJRo8OpVSLFkd"
DEFAULT_CLUSTER = "volcano_icl"
DEFAULT_VOICE_TYPE = "S_FwdJnJNN1"
HOST = "openspeech.bytedance.com"
API_URL = f"wss://{HOST}/api/v1/tts/ws_binary"

# version: b0001 (4 bits)
# header size: b0001 (4 bits)
# message type: b0001 (Full client request) (4bits)
# message type specific flags: b0000 (none) (4bits)
# message serialization method: b0001 (JSON) (4 bits)
# message compression: b0001 (gzip) (4bits)
# reserved data: 0x00 (1 byte)
default_header = bytearray(b'\x11\x10\x11\x00')

request_json_template = {
    "app": {
        "appid": DEFAULT_APPID,
        "token": "access_token",
        "cluster": DEFAULT_CLUSTER
    },
    "user": {
        "uid": "388808087185088"
    },
    "audio": {
        "voice_type": DEFAULT_VOICE_TYPE,
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
    def __init__(self, appid=DEFAULT_APPID, token=DEFAULT_TOKEN, cluster=DEFAULT_CLUSTER):
        self.appid = appid
        self.token = token
        self.cluster = cluster
        self.api_url = API_URL
        self.header = {"Authorization": f"Bearer; {self.token}"}

    async def _synthesize_async(self, text: str, output_path: str, voice_type=DEFAULT_VOICE_TYPE):
        submit_request_json = copy.deepcopy(request_json_template)
        submit_request_json["app"]["appid"] = self.appid
        submit_request_json["app"]["token"] = self.token # 注意：虽然 template 里写的是 token，但实际可能不需要在 json 里传 token，只要 header 里有
        submit_request_json["app"]["cluster"] = self.cluster
        submit_request_json["audio"]["voice_type"] = voice_type
        submit_request_json["request"]["reqid"] = str(uuid.uuid4())
        submit_request_json["request"]["text"] = text
        submit_request_json["request"]["operation"] = "submit"
        
        payload_bytes = str.encode(json.dumps(submit_request_json))
        payload_bytes = gzip.compress(payload_bytes)  # if no compression, comment this line
        full_client_request = bytearray(default_header)
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        full_client_request.extend(payload_bytes)  # payload
        
        # logger.info(f"Requesting TTS for: {text}")
        
        try:
            async with websockets.connect(self.api_url, extra_headers=self.header, ping_interval=None) as ws:
                await ws.send(full_client_request)
                
                with open(output_path, "wb") as file_to_save:
                    while True:
                        res = await ws.recv()
                        done = self._parse_response(res, file_to_save)
                        if done:
                            break
                # logger.info(f"TTS finished, saved to {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise

    def _parse_response(self, res, file):
        # print(f"response raw bytes: {res}")
        protocol_version = res[0] >> 4
        header_size = res[0] & 0x0f
        message_type = res[1] >> 4
        message_type_specific_flags = res[1] & 0x0f
        serialization_method = res[2] >> 4
        message_compression = res[2] & 0x0f
        reserved = res[3]
        header_extensions = res[4:header_size*4]
        payload = res[header_size*4:]
        
        if message_type == 0xb:  # audio-only server response
            if message_type_specific_flags == 0:  # no sequence number as ACK
                # print("Payload size: 0")
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
            # print(f"Frontend message: {payload}")
            return False
        else:
            # print("undefined message type!")
            return True

    def synthesize(self, text: str, output_path: str = "output.mp3", voice_type=DEFAULT_VOICE_TYPE) -> str:
        """
        同步接口：合成语音并保存到文件
        """
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
