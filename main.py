#!/usr/bin/env python3
"""
VRChat OSC Controller - 完整版
支持所有VRChat OSC参数：Avatar参数、Input控制、Chatbox、Camera等
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from aiohttp import web
import aiohttp
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# 配置
OSC_SEND_IP = "127.0.0.1"
OSC_SEND_PORT = 9000  # 发送到VRChat
OSC_RECEIVE_PORT = 9001  # 接收来自VRChat
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

# 参数配置文件路径
CONFIG_FILE = "avtr_46040475-8cfe-410f-9744-cdaa117887bc.json"


@dataclass
class Parameter:
    name: str
    address: str
    param_type: str
    value: Any = None
    min_val: float = 0.0
    max_val: float = 1.0
    is_input: bool = False
    is_output: bool = False
    category: str = "avatar"  # 参数类别


# 系统级OSC参数定义
SYSTEM_PARAMETERS = {
    # ===== Input 控制 (Write-only) =====
    "Input_Horizontal": {"address": "/input/Horizontal", "type": "Float", "min": -1.0, "max": 1.0, "category": "input"},
    "Input_Vertical": {"address": "/input/Vertical", "type": "Float", "min": -1.0, "max": 1.0, "category": "input"},
    "Input_LookHorizontal": {"address": "/input/LookHorizontal", "type": "Float", "min": -1.0, "max": 1.0, "category": "input"},
    "Input_LookVertical": {"address": "/input/LookVertical", "type": "Float", "min": -1.0, "max": 1.0, "category": "input"},
    "Input_Jump": {"address": "/input/Jump", "type": "Bool", "category": "input"},
    "Input_Run": {"address": "/input/Run", "type": "Bool", "category": "input"},
    "Input_Voice": {"address": "/input/Voice", "type": "Bool", "category": "input"},
    "Input_MoveForward": {"address": "/input/MoveForward", "type": "Bool", "category": "input"},
    "Input_MoveBackward": {"address": "/input/MoveBackward", "type": "Bool", "category": "input"},
    "Input_MoveLeft": {"address": "/input/MoveLeft", "type": "Bool", "category": "input"},
    "Input_MoveRight": {"address": "/input/MoveRight", "type": "Bool", "category": "input"},
    "Input_GrabLeft": {"address": "/input/GrabLeft", "type": "Bool", "category": "input"},
    "Input_UseLeft": {"address": "/input/UseLeft", "type": "Bool", "category": "input"},
    "Input_DropLeft": {"address": "/input/DropLeft", "type": "Bool", "category": "input"},
    "Input_GrabRight": {"address": "/input/GrabRight", "type": "Bool", "category": "input"},
    "Input_UseRight": {"address": "/input/UseRight", "type": "Bool", "category": "input"},
    "Input_DropRight": {"address": "/input/DropRight", "type": "Bool", "category": "input"},
    "Input_LookLeft": {"address": "/input/LookLeft", "type": "Bool", "category": "input"},
    "Input_LookRight": {"address": "/input/LookRight", "type": "Bool", "category": "input"},
    "Input_ComfortLeft": {"address": "/input/ComfortLeft", "type": "Bool", "category": "input"},
    "Input_ComfortRight": {"address": "/input/ComfortRight", "type": "Bool", "category": "input"},
    "Input_AFKToggle": {"address": "/input/AFKToggle", "type": "Bool", "category": "input"},
    
    # ===== Chatbox 控制 =====
    "Chatbox_Typing": {"address": "/chatbox/typing", "type": "Bool", "category": "chatbox"},
    
    # ===== Camera 控制 (Read-Write) =====
    "Camera_Mode": {"address": "/usercamera/Mode", "type": "Int", "min": 0, "max": 6, "category": "camera"},
    "Camera_Zoom": {"address": "/usercamera/Zoom", "type": "Float", "min": 20, "max": 150, "category": "camera"},
    "Camera_Exposure": {"address": "/usercamera/Exposure", "type": "Float", "min": -10, "max": 4, "category": "camera"},
    "Camera_FocalDistance": {"address": "/usercamera/FocalDistance", "type": "Float", "min": 0, "max": 10, "category": "camera"},
    "Camera_Aperture": {"address": "/usercamera/Aperture", "type": "Float", "min": 1.4, "max": 32, "category": "camera"},
    "Camera_Capture": {"address": "/usercamera/Capture", "type": "Bool", "category": "camera"},
    "Camera_CaptureDelayed": {"address": "/usercamera/CaptureDelayed", "type": "Bool", "category": "camera"},
    "Camera_Close": {"address": "/usercamera/Close", "type": "Bool", "category": "camera"},
    "Camera_ShowUIInCamera": {"address": "/usercamera/ShowUIInCamera", "type": "Bool", "category": "camera"},
    "Camera_LocalPlayer": {"address": "/usercamera/LocalPlayer", "type": "Bool", "category": "camera"},
    "Camera_RemotePlayer": {"address": "/usercamera/RemotePlayer", "type": "Bool", "category": "camera"},
    "Camera_Environment": {"address": "/usercamera/Environment", "type": "Bool", "category": "camera"},
    "Camera_GreenScreen": {"address": "/usercamera/GreenScreen", "type": "Bool", "category": "camera"},
    "Camera_Lock": {"address": "/usercamera/Lock", "type": "Bool", "category": "camera"},
    "Camera_SmoothMovement": {"address": "/usercamera/SmoothMovement", "type": "Bool", "category": "camera"},
    "Camera_LookAtMe": {"address": "/usercamera/LookAtMe", "type": "Bool", "category": "camera"},
    "Camera_Flying": {"address": "/usercamera/Flying", "type": "Bool", "category": "camera"},
    "Camera_Streaming": {"address": "/usercamera/Streaming", "type": "Bool", "category": "camera"},
    
    # ===== 系统信息 (Read-only) =====
    "System_AvatarID": {"address": "/avatar/change", "type": "String", "category": "system"},
    "System_VRMode": {"address": "/avatar/parameters/VRMode", "type": "Int", "category": "system"},
    "System_TrackingType": {"address": "/avatar/parameters/TrackingType", "type": "Int", "category": "system"},
    "System_EyeHeightAsMeters": {"address": "/avatar/parameters/EyeHeightAsMeters", "type": "Float", "category": "system"},
    "System_EyeHeightAsPercent": {"address": "/avatar/parameters/EyeHeightAsPercent", "type": "Float", "category": "system"},
    
    # ===== Tracking 系统输出 (Read-only) =====
    "Tracking_HeadPosX": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 0, "category": "tracking"},
    "Tracking_HeadPosY": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 1, "category": "tracking"},
    "Tracking_HeadPosZ": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 2, "category": "tracking"},
    "Tracking_HeadRotX": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 3, "category": "tracking"},
    "Tracking_HeadRotY": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 4, "category": "tracking"},
    "Tracking_HeadRotZ": {"address": "/tracking/vrsystem/head/pose", "type": "Float", "index": 5, "category": "tracking"},
}


class OSCManager:
    def __init__(self, controller):
        self.controller = controller
        self.client: Optional[SimpleUDPClient] = None
        self.server: Optional[AsyncIOOSCUDPServer] = None
        self.dispatcher = Dispatcher()
        self.transport = None
        self.message_queue = asyncio.Queue()
        self._running = False
        
    def setup(self):
        """初始化OSC客户端和服务器"""
        # OSC客户端 - 发送给VRChat
        self.client = SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)
        
        # 设置OSC消息处理器
        # Avatar参数
        self.dispatcher.map("/avatar/parameters/*", self._handle_avatar_messages)
        # Avatar变化
        self.dispatcher.map("/avatar/change", self._handle_avatar_change)
        # 相机参数
        self.dispatcher.map("/usercamera/*", self._handle_camera_messages)
        # Tracking参数
        self.dispatcher.map("/tracking/vrsystem/*/pose", self._handle_tracking_messages)
        # 默认处理器
        self.dispatcher.set_default_handler(self._handle_unknown_message)
        
    def _handle_avatar_messages(self, address: str, *args):
        """处理Avatar参数消息"""
        if not args:
            return
        value = args[0]
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                self.message_queue.put_nowait, ("avatar", address, value)
            )
        except:
            pass
    
    def _handle_avatar_change(self, address: str, *args):
        """处理Avatar切换消息"""
        if not args:
            return
        avatar_id = args[0] if isinstance(args[0], str) else str(args[0])
        print(f"[OSC] Avatar changed: {avatar_id}")
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                self.message_queue.put_nowait, ("system", "/avatar/change", avatar_id)
            )
        except:
            pass
    
    def _handle_camera_messages(self, address: str, *args):
        """处理相机参数消息"""
        if not args:
            return
        value = args[0]
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                self.message_queue.put_nowait, ("camera", address, value)
            )
        except:
            pass
    
    def _handle_tracking_messages(self, address: str, *args):
        """处理Tracking消息 (6个float值)"""
        if len(args) < 6:
            return
        # 存储完整的pose数据
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                self.message_queue.put_nowait, ("tracking", address, list(args[:6]))
            )
        except:
            pass
    
    def _handle_unknown_message(self, address: str, *args):
        """处理未知的OSC消息"""
        if args:
            print(f"[OSC] Unknown message: {address} {args}")
        
    async def process_messages(self):
        """处理消息队列"""
        while self._running:
            try:
                category, address, value = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.1
                )
                
                # 查找对应的参数
                for name, param in self.controller.parameters.items():
                    if param.category != category:
                        continue
                    
                    # 特殊处理tracking (多值)
                    if category == "tracking" and isinstance(value, list):
                        if param.address == address:
                            idx = SYSTEM_PARAMETERS.get(name, {}).get("index", 0)
                            if idx < len(value):
                                param.value = value[idx]
                                await self.controller.broadcast({
                                    "type": "output",
                                    "name": name,
                                    "value": param.value,
                                    "category": category
                                })
                    elif param.address == address:
                        param.value = value
                        await self.controller.broadcast({
                            "type": "output",
                            "name": name,
                            "value": value,
                            "category": category
                        })
                        break
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[OSC] Process error: {e}")
        
    async def start_server(self):
        """启动OSC接收服务器"""
        loop = asyncio.get_event_loop()
        self.server = AsyncIOOSCUDPServer(
            ("0.0.0.0", OSC_RECEIVE_PORT),
            self.dispatcher,
            loop
        )
        self.transport, protocol = await self.server.create_serve_endpoint()
        self._running = True
        
        # 启动消息处理任务
        asyncio.create_task(self.process_messages())
        
        print(f"[OSC] Server listening on port {OSC_RECEIVE_PORT}")
        
    async def stop_server(self):
        """停止OSC服务器"""
        self._running = False
        if self.transport:
            self.transport.close()
            
    def send(self, address: str, value: Any):
        """发送OSC消息到VRChat"""
        if self.client:
            self.client.send_message(address, value)
            print(f"[OSC] Sent: {address} = {value}")


class VRChatController:
    def __init__(self):
        self.parameters: Dict[str, Parameter] = {}
        self.websockets: set = set()
        self.osc = OSCManager(self)
        
    def load_config(self):
        """加载参数配置 (JSON文件 + 系统参数)"""
        # 1. 加载系统参数
        for name, config in SYSTEM_PARAMETERS.items():
            param = Parameter(
                name=name,
                address=config["address"],
                param_type=config["type"],
                min_val=config.get("min", 0.0),
                max_val=config.get("max", 1.0),
                is_input=True,
                is_output=(config["category"] in ["system", "camera", "tracking"]),
                category=config["category"]
            )
            self.parameters[name] = param
        
        # 2. 加载Avatar参数
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                
            for p in config.get("parameters", []):
                name = p["name"]
                
                # Input参数
                if "input" in p:
                    inp = p["input"]
                    param_type = inp["type"]
                    
                    min_val, max_val = 0.0, 1.0
                    if param_type == "Int":
                        min_val, max_val = 0, 8
                    elif param_type == "Float":
                        min_val, max_val = 0.0, 1.0
                    elif param_type == "Bool":
                        min_val, max_val = 0, 1
                    
                    # 如果系统参数中已存在，更新它
                    if name in self.parameters:
                        self.parameters[name].is_input = True
                        self.parameters[name].min_val = min_val
                        self.parameters[name].max_val = max_val
                    else:
                        param = Parameter(
                            name=name,
                            address=inp["address"],
                            param_type=param_type,
                            min_val=min_val,
                            max_val=max_val,
                            is_input=True,
                            category="avatar"
                        )
                        self.parameters[name] = param
                
                # Output参数
                if "output" in p:
                    out = p["output"]
                    param_type = out["type"]
                    
                    min_val, max_val = 0.0, 1.0
                    if param_type == "Int":
                        min_val, max_val = 0, 255
                    elif param_type == "Float":
                        min_val, max_val = -1.0, 1.0
                    elif param_type == "Bool":
                        min_val, max_val = 0, 1
                    
                    if name in self.parameters:
                        self.parameters[name].is_output = True
                    else:
                        param = Parameter(
                            name=name,
                            address=out["address"],
                            param_type=param_type,
                            min_val=min_val,
                            max_val=max_val,
                            is_output=True,
                            category="avatar"
                        )
                        self.parameters[name] = param
        
        print(f"[Config] Loaded {len(self.parameters)} parameters")
        
    def get_parameter_list(self) -> List[Dict]:
        """获取参数列表供前端使用"""
        result = []
        for name, param in self.parameters.items():
            result.append({
                "name": name,
                "type": param.param_type,
                "address": param.address,
                "min": param.min_val,
                "max": param.max_val,
                "isInput": param.is_input,
                "isOutput": param.is_output,
                "value": param.value,
                "category": param.category
            })
        return result
        
    async def broadcast(self, message: Dict):
        """广播消息给所有WebSocket客户端"""
        if not self.websockets:
            return
        
        disconnected = set()
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[WebSocket] Send error: {e}")
                disconnected.add(ws)
        
        self.websockets -= disconnected
        
    async def handle_websocket(self, request):
        """处理WebSocket连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        print(f"[WebSocket] Client connected")
        self.websockets.add(ws)
        
        # 发送初始参数列表
        await ws.send_json({
            "type": "init",
            "parameters": self.get_parameter_list()
        })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_message(data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"[WebSocket] Error: {ws.exception()}")
        except Exception as e:
            print(f"[WebSocket] Handler error: {e}")
        finally:
            self.websockets.discard(ws)
            print(f"[WebSocket] Client disconnected")
            
        return ws
        
    async def handle_message(self, data: Dict):
        """处理前端发来的消息"""
        msg_type = data.get("type")
        
        if msg_type == "set":
            name = data.get("name")
            value = data.get("value")
            
            if name in self.parameters:
                param = self.parameters[name]
                param.value = value
                
                # 根据参数类型转换值
                send_value = value
                if param.param_type == "Float":
                    send_value = float(value)
                elif param.param_type == "Int":
                    send_value = int(value)
                elif param.param_type == "Bool":
                    send_value = bool(value)
                
                # 发送给VRChat
                self.osc.send(param.address, send_value)
                
                # 广播给其他客户端
                await self.broadcast({
                    "type": "input",
                    "name": name,
                    "value": value,
                    "category": param.category
                })
        
        elif msg_type == "chatbox":
            # 处理聊天框消息
            text = data.get("text", "")
            send_immediately = data.get("send", True)
            notification = data.get("notification", True)
            
            if self.osc.client:
                # /chatbox/input expects: string, bool, bool
                self.osc.client.send_message("/chatbox/input", [text, send_immediately, notification])
                print(f"[OSC] Chatbox: {text}")


# 全局控制器实例
controller = VRChatController()


async def index_handler(request):
    """处理首页请求"""
    return web.FileResponse('./static/index.html')


async def init_app():
    """初始化应用"""
    # 加载配置
    controller.load_config()
    
    # 设置OSC
    controller.osc.setup()
    await controller.osc.start_server()
    
    # 创建Web应用
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', controller.handle_websocket)
    app.router.add_static('/static/', path='./static', name='static')
    
    return app


async def main():
    """主函数"""
    app = await init_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    
    print(f"[Web] Server started at http://localhost:{WEB_PORT}")
    print(f"[OSC] Sending to {OSC_SEND_IP}:{OSC_SEND_PORT}")
    print(f"[OSC] Receiving on port {OSC_RECEIVE_PORT}")
    print("\n按 Ctrl+C 停止程序\n")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止...")
        await controller.osc.stop_server()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())