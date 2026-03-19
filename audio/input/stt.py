import asyncio
import aiohttp
import json
import struct
import gzip
import uuid
import logging
import os
import subprocess
import tempfile
from typing import Optional, List, Dict, Any, Tuple

# 配置日志
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_SAMPLE_RATE = 16000

class ProtocolVersion:
    V1 = 0b0001

class MessageType:
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111

class MessageTypeSpecificFlags:
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011

class SerializationType:
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001

class CompressionType:
    GZIP = 0b0001

class CommonUtils:
    @staticmethod
    def gzip_compress(data: bytes) -> bytes:
        return gzip.compress(data)

    @staticmethod
    def gzip_decompress(data: bytes) -> bytes:
        return gzip.decompress(data)

    @staticmethod
    def convert_wav_with_path(audio_path: str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(sample_rate),
            tmp_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(tmp_path, "rb") as f:
            wav_data = f.read()
        os.remove(tmp_path)
        return wav_data

    @staticmethod
    def read_wav_info(data: bytes) -> Tuple[int, int, int, int, bytes]:
        pos = 36
        while pos < len(data) - 8:
            subchunk_id = data[pos:pos+4]
            subchunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            if subchunk_id == b'data':
                wave_data = data[pos+8:pos+8+subchunk_size]
                return (1, 16, 16000, subchunk_size // 2, wave_data)
            pos += 8 + subchunk_size
        raise ValueError("Invalid WAV file")

class AsrRequestHeader:
    def __init__(self):
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def to_bytes(self) -> bytes:
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

class STTClient:
    """
    适配 main.py 的语音转文字客户端
    """
    def __init__(self):
        self.app_key = "2078616776"
        self.access_key = "7KpKwBDOlRBlEXB6sbcIyhJa-01pUa-U"
        self.url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
        self.segment_duration = 200

    def recognize(self, file_path: str) -> str:
        """
        同步调用入口，供 main.py 使用
        """
        try:
            return asyncio.run(self._async_recognize(file_path))
        except Exception as e:
            logger.error(f"STT recognition error: {e}")
            return ""

    async def _async_recognize(self, file_path: str) -> str:
        # 1. 预处理音频
        content = CommonUtils.convert_wav_with_path(file_path, 16000)
        _, _, _, _, pcm_data = CommonUtils.read_wav_info(content)
        
        # 2. 分片
        segment_size = (16000 * 2) * self.segment_duration // 1000
        segments = [pcm_data[i:i + segment_size] for i in range(0, len(pcm_data), segment_size)]
        
        headers = {
            "X-Api-Resource-Id": "volc.seedasr.sauc.duration",
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Api-Access-Key": self.access_key,
            "X-Api-App-Key": self.app_key
        }

        final_text = ""
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.url, headers=headers) as ws:
                # 发送配置包
                conf_req = self._build_full_request()
                await ws.send_bytes(conf_req)
                
                # 发送音频包
                for i, seg in enumerate(segments):
                    is_last = (i == len(segments) - 1)
                    audio_req = self._build_audio_request(i + 2, seg, is_last)
                    await ws.send_bytes(audio_req)

                # 接收结果
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        resp_data = self._parse_response(msg.data)
                        if resp_data.get("is_last_package"):
                            payload = resp_data.get("payload_msg")
                            if payload and "result" in payload:
                                final_text = payload["result"].get("text", "")
                            break
        return final_text

    def _build_full_request(self) -> bytes:
        header = AsrRequestHeader()
        payload = {
            "user": {"uid": "demo_uid"},
            "audio": {"format": "pcm", "codec": "raw", "rate": 16000, "bits": 16, "channel": 1},
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "show_utterances": True,
                "enable_nonstream": True
            }
        }
        p_bytes = CommonUtils.gzip_compress(json.dumps(payload).encode('utf-8'))
        return header.to_bytes() + struct.pack('>i', 1) + struct.pack('>I', len(p_bytes)) + p_bytes

    def _build_audio_request(self, seq: int, segment: bytes, is_last: bool) -> bytes:
        header = AsrRequestHeader()
        header.message_type = MessageType.CLIENT_AUDIO_ONLY_REQUEST
        if is_last:
            header.message_type_specific_flags = MessageTypeSpecificFlags.NEG_WITH_SEQUENCE
            seq = -seq
        p_bytes = CommonUtils.gzip_compress(segment)
        return header.to_bytes() + struct.pack('>i', seq) + struct.pack('>I', len(p_bytes)) + p_bytes

    def _parse_response(self, msg: bytes) -> Dict[str, Any]:
        h_size = msg[0] & 0x0f
        m_type = msg[1] >> 4
        m_flags = msg[1] & 0x0f
        m_comp = msg[2] & 0x0f
        payload = msg[h_size*4:]
        
        res = {"is_last_package": False, "payload_msg": None}
        
        if m_flags & 0x01: payload = payload[4:] # skip seq
        if m_flags & 0x02: res["is_last_package"] = True
        if m_flags & 0x04: payload = payload[4:] # skip event
            
        if m_type == MessageType.SERVER_FULL_RESPONSE:
            payload = payload[4:] # skip size
        elif m_type == MessageType.SERVER_ERROR_RESPONSE:
            return res
            
        if payload and m_comp == CompressionType.GZIP:
            payload = CommonUtils.gzip_decompress(payload)
        if payload:
            res["payload_msg"] = json.loads(payload.decode('utf-8'))
        return res

if __name__ == "__main__":
    # 简单测试
    client = STTClient()
    # 确保目录下有一个测试文件
    # print(client.recognize("test.wav"))