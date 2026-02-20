#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VRChat OSC Controller - 基于 VRChat Wiki 官方参数规范
支持标准 OSC 参数，可选 JSON 文件扩展
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




@dataclass
class Parameter:
    """VRChat OSC 参数数据类
    
    表示一个VRChat OSC参数，包含参数的所有元数据和当前值。
    
    属性:
        name: 参数名称（唯一标识符）
        address: OSC地址（如"/input/Horizontal"）
        param_type: 参数类型（"Float"、"Int"、"Bool"、"String"）
        value: 当前参数值
        min_val: 最小值（对于数值类型）
        max_val: 最大值（对于数值类型）
        is_input: 是否为输入参数（可向VRChat发送）
        is_output: 是否为输出参数（可从VRChat接收）
        category: 参数类别（"input"、"avatar"、"camera"、"tracking"等）
        description: 参数描述
        display_name: 显示名称（用于前端界面）
    """
    name: str
    address: str
    param_type: str
    value: Any = None
    min_val: float = 0.0
    max_val: float = 1.0
    is_input: bool = False
    is_output: bool = False
    category: str = "avatar"  # 参数类别
    description: str = ""  # 参数描述
    display_name: str = ""  # 中文显示名


# ==================== VRChat Wiki 官方 OSC 参数定义 ====================
# 来源: https://wiki.vrchat.com/wiki/Open_Sound_Control

WIKI_PARAMETERS = {
    # ===== Input Axes (Write-only) =====
    "Input_Horizontal": {
        "address": "/input/Horizontal",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "水平移动",
        "description": "左右移动控制"
    },
    "Input_Vertical": {
        "address": "/input/Vertical",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "垂直移动",
        "description": "前后移动控制"
    },
    "Input_LookHorizontal": {
        "address": "/input/LookHorizontal",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "水平视角",
        "description": "左右视角旋转"
    },
    "Input_LookVertical": {
        "address": "/input/LookVertical",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "垂直视角",
        "description": "上下视角旋转"
    },
    "Input_SpinHoldCwCcw": {
        "address": "/input/SpinHoldCwCcw",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "物品旋转左右",
        "description": "手持物品顺时针/逆时针旋转"
    },
    "Input_SpinHoldUD": {
        "address": "/input/SpinHoldUD",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "物品旋转上下",
        "description": "手持物品上下旋转"
    },
    "Input_SpinHoldLR": {
        "address": "/input/SpinHoldLR",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "物品旋转左右",
        "description": "手持物品左右旋转"
    },
    "Input_MoveHoldFB": {
        "address": "/input/MoveHoldFB",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "物品移动前后",
        "description": "手持物品前后移动"
    },
    "Input_UseAxisRight": {
        "address": "/input/UseAxisRight",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "右手使用轴",
        "description": "右手持物使用轴"
    },
    "Input_GrabAxisRight": {
        "address": "/input/GrabAxisRight",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "input",
        "display_name": "右手抓取轴",
        "description": "右手持物抓取轴"
    },

    # ===== Input Buttons (Write-only) =====
    "Input_Jump": {
        "address": "/input/Jump",
        "type": "Bool",
        "category": "input",
        "display_name": "跳跃",
        "description": "跳跃动作"
    },
    "Input_Run": {
        "address": "/input/Run",
        "type": "Bool",
        "category": "input",
        "display_name": "奔跑",
        "description": "奔跑动作"
    },
    "Input_Voice": {
        "address": "/input/Voice",
        "type": "Bool",
        "category": "input",
        "display_name": "语音开关",
        "description": "麦克风开关"
    },
    "Input_MoveForward": {
        "address": "/input/MoveForward",
        "type": "Bool",
        "category": "input",
        "display_name": "向前移动",
        "description": "向前移动"
    },
    "Input_MoveBackward": {
        "address": "/input/MoveBackward",
        "type": "Bool",
        "category": "input",
        "display_name": "向后移动",
        "description": "向后移动"
    },
    "Input_MoveLeft": {
        "address": "/input/MoveLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "向左移动",
        "description": "向左移动"
    },
    "Input_MoveRight": {
        "address": "/input/MoveRight",
        "type": "Bool",
        "category": "input",
        "display_name": "向右移动",
        "description": "向右移动"
    },
    "Input_LookLeft": {
        "address": "/input/LookLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "向左看",
        "description": "向左旋转视角"
    },
    "Input_LookRight": {
        "address": "/input/LookRight",
        "type": "Bool",
        "category": "input",
        "display_name": "向右看",
        "description": "向右旋转视角"
    },
    "Input_ComfortLeft": {
        "address": "/input/ComfortLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "舒适左转",
        "description": "VR快速左转"
    },
    "Input_ComfortRight": {
        "address": "/input/ComfortRight",
        "type": "Bool",
        "category": "input",
        "display_name": "舒适右转",
        "description": "VR快速右转"
    },
    "Input_GrabLeft": {
        "address": "/input/GrabLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "左手抓取",
        "description": "左手抓取物品"
    },
    "Input_UseLeft": {
        "address": "/input/UseLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "左手使用",
        "description": "左手使用物品"
    },
    "Input_DropLeft": {
        "address": "/input/DropLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "左手丢弃",
        "description": "左手丢弃物品"
    },
    "Input_GrabRight": {
        "address": "/input/GrabRight",
        "type": "Bool",
        "category": "input",
        "display_name": "右手抓取",
        "description": "右手抓取物品"
    },
    "Input_UseRight": {
        "address": "/input/UseRight",
        "type": "Bool",
        "category": "input",
        "display_name": "右手使用",
        "description": "右手使用物品"
    },
    "Input_DropRight": {
        "address": "/input/DropRight",
        "type": "Bool",
        "category": "input",
        "display_name": "右手丢弃",
        "description": "右手丢弃物品"
    },
    "Input_AFKToggle": {
        "address": "/input/AFKToggle",
        "type": "Bool",
        "category": "input",
        "display_name": "AFK切换",
        "description": "离开状态切换"
    },
    "Input_ToggleSitStand": {
        "address": "/input/ToggleSitStand",
        "type": "Bool",
        "category": "input",
        "display_name": "坐站切换",
        "description": "坐姿站姿切换"
    },
    "Input_PanicButton": {
        "address": "/input/PanicButton",
        "type": "Bool",
        "category": "input",
        "display_name": "紧急按钮",
        "description": "安全模式"
    },
    "Input_QuickMenuToggleLeft": {
        "address": "/input/QuickMenuToggleLeft",
        "type": "Bool",
        "category": "input",
        "display_name": "左手菜单",
        "description": "左手快捷菜单"
    },
    "Input_QuickMenuToggleRight": {
        "address": "/input/QuickMenuToggleRight",
        "type": "Bool",
        "category": "input",
        "display_name": "右手菜单",
        "description": "右手快捷菜单"
    },

    # ===== Chatbox (Write-only) =====
    "Chatbox_Typing": {
        "address": "/chatbox/typing",
        "type": "Bool",
        "category": "chatbox",
        "display_name": "输入中",
        "description": "聊天框输入指示器"
    },

    # ===== Camera (Read-Write) =====
    "Camera_Mode": {
        "address": "/usercamera/Mode",
        "type": "Int",
        "min": 0,
        "max": 6,
        "category": "camera",
        "display_name": "相机模式",
        "description": "相机工作模式"
    },
    "Camera_Capture": {
        "address": "/usercamera/Capture",
        "type": "Bool",
        "category": "camera",
        "display_name": "拍照",
        "description": "拍摄照片"
    },
    "Camera_CaptureDelayed": {
        "address": "/usercamera/CaptureDelayed",
        "type": "Bool",
        "category": "camera",
        "display_name": "延时拍照",
        "description": "延时拍摄"
    },
    "Camera_Close": {
        "address": "/usercamera/Close",
        "type": "Bool",
        "category": "camera",
        "display_name": "关闭相机",
        "description": "关闭相机"
    },
    "Camera_Zoom": {
        "address": "/usercamera/Zoom",
        "type": "Float",
        "min": 20,
        "max": 150,
        "category": "camera",
        "display_name": "缩放",
        "description": "相机缩放"
    },
    "Camera_Exposure": {
        "address": "/usercamera/Exposure",
        "type": "Float",
        "min": -10,
        "max": 4,
        "category": "camera",
        "display_name": "曝光",
        "description": "相机曝光"
    },
    "Camera_FocalDistance": {
        "address": "/usercamera/FocalDistance",
        "type": "Float",
        "min": 0,
        "max": 10,
        "category": "camera",
        "display_name": "焦距",
        "description": "相机焦距"
    },
    "Camera_Aperture": {
        "address": "/usercamera/Aperture",
        "type": "Float",
        "min": 1.4,
        "max": 32,
        "category": "camera",
        "display_name": "光圈",
        "description": "相机光圈"
    },
    "Camera_Hue": {
        "address": "/usercamera/Hue",
        "type": "Float",
        "min": 0,
        "max": 360,
        "category": "camera",
        "display_name": "色相",
        "description": "绿幕色相"
    },
    "Camera_Saturation": {
        "address": "/usercamera/Saturation",
        "type": "Float",
        "min": 0,
        "max": 100,
        "category": "camera",
        "display_name": "饱和度",
        "description": "绿幕饱和度"
    },
    "Camera_Lightness": {
        "address": "/usercamera/Lightness",
        "type": "Float",
        "min": 0,
        "max": 50,
        "category": "camera",
        "display_name": "亮度",
        "description": "绿幕亮度"
    },
    "Camera_LookAtMeXOffset": {
        "address": "/usercamera/LookAtMeXOffset",
        "type": "Float",
        "min": -25,
        "max": 25,
        "category": "camera",
        "display_name": "看我X偏移",
        "description": "看向我X轴偏移"
    },
    "Camera_LookAtMeYOffset": {
        "address": "/usercamera/LookAtMeYOffset",
        "type": "Float",
        "min": -25,
        "max": 25,
        "category": "camera",
        "display_name": "看我Y偏移",
        "description": "看向我Y轴偏移"
    },
    "Camera_FlySpeed": {
        "address": "/usercamera/FlySpeed",
        "type": "Float",
        "min": 0.1,
        "max": 15,
        "category": "camera",
        "display_name": "飞行速度",
        "description": "相机飞行速度"
    },
    "Camera_TurnSpeed": {
        "address": "/usercamera/TurnSpeed",
        "type": "Float",
        "min": 0.1,
        "max": 5,
        "category": "camera",
        "display_name": "转向速度",
        "description": "相机转向速度"
    },
    "Camera_SmoothingStrength": {
        "address": "/usercamera/SmoothingStrength",
        "type": "Float",
        "min": 0.1,
        "max": 10,
        "category": "camera",
        "display_name": "平滑强度",
        "description": "相机平滑强度"
    },
    "Camera_PhotoRate": {
        "address": "/usercamera/PhotoRate",
        "type": "Float",
        "min": 0.1,
        "max": 2,
        "category": "camera",
        "display_name": "拍照速率",
        "description": "轨道拍照速率"
    },
    "Camera_Duration": {
        "address": "/usercamera/Duration",
        "type": "Float",
        "min": 0.1,
        "max": 60,
        "category": "camera",
        "display_name": "持续时间",
        "description": "轨道持续时间"
    },
    "Camera_ShowUIInCamera": {
        "address": "/usercamera/ShowUIInCamera",
        "type": "Bool",
        "category": "camera",
        "display_name": "相机显示UI",
        "description": "在相机中显示UI"
    },
    "Camera_LocalPlayer": {
        "address": "/usercamera/LocalPlayer",
        "type": "Bool",
        "category": "camera",
        "display_name": "本地玩家",
        "description": "显示本地玩家"
    },
    "Camera_RemotePlayer": {
        "address": "/usercamera/RemotePlayer",
        "type": "Bool",
        "category": "camera",
        "display_name": "远程玩家",
        "description": "显示远程玩家"
    },
    "Camera_Environment": {
        "address": "/usercamera/Environment",
        "type": "Bool",
        "category": "camera",
        "display_name": "环境",
        "description": "显示环境"
    },
    "Camera_GreenScreen": {
        "address": "/usercamera/GreenScreen",
        "type": "Bool",
        "category": "camera",
        "display_name": "绿幕",
        "description": "启用绿幕"
    },
    "Camera_Lock": {
        "address": "/usercamera/Lock",
        "type": "Bool",
        "category": "camera",
        "display_name": "锁定相机",
        "description": "锁定相机位置"
    },
    "Camera_SmoothMovement": {
        "address": "/usercamera/SmoothMovement",
        "type": "Bool",
        "category": "camera",
        "display_name": "平滑移动",
        "description": "启用平滑移动"
    },
    "Camera_LookAtMe": {
        "address": "/usercamera/LookAtMe",
        "type": "Bool",
        "category": "camera",
        "display_name": "看向我",
        "description": "相机看向我"
    },
    "Camera_AutoLevelRoll": {
        "address": "/usercamera/AutoLevelRoll",
        "type": "Bool",
        "category": "camera",
        "display_name": "自动水平 roll",
        "description": "自动水平校正 roll"
    },
    "Camera_AutoLevelPitch": {
        "address": "/usercamera/AutoLevelPitch",
        "type": "Bool",
        "category": "camera",
        "display_name": "自动水平 pitch",
        "description": "自动水平校正 pitch"
    },
    "Camera_Flying": {
        "address": "/usercamera/Flying",
        "type": "Bool",
        "category": "camera",
        "display_name": "飞行模式",
        "description": "相机飞行模式"
    },
    "Camera_TriggerTakesPhotos": {
        "address": "/usercamera/TriggerTakesPhotos",
        "type": "Bool",
        "category": "camera",
        "display_name": "触发拍照",
        "description": "触发器拍照"
    },
    "Camera_DollyPathsStayVisible": {
        "address": "/usercamera/DollyPathsStayVisible",
        "type": "Bool",
        "category": "camera",
        "display_name": "显示轨道",
        "description": "轨道路径保持可见"
    },
    "Camera_AudioFromCamera": {
        "address": "/usercamera/AudioFromCamera",
        "type": "Bool",
        "category": "camera",
        "display_name": "相机音频",
        "description": "从相机获取音频"
    },
    "Camera_ShowFocus": {
        "address": "/usercamera/ShowFocus",
        "type": "Bool",
        "category": "camera",
        "display_name": "显示焦点",
        "description": "显示对焦层"
    },
    "Camera_Streaming": {
        "address": "/usercamera/Streaming",
        "type": "Bool",
        "category": "camera",
        "display_name": "推流",
        "description": "Spout推流"
    },
    "Camera_RollWhileFlying": {
        "address": "/usercamera/RollWhileFlying",
        "type": "Bool",
        "category": "camera",
        "display_name": "飞行时Roll",
        "description": "飞行时允许Roll"
    },
    "Camera_OrientationIsLandscape": {
        "address": "/usercamera/OrientationIsLandscape",
        "type": "Bool",
        "category": "camera",
        "display_name": "横屏",
        "description": "图像横屏方向"
    },

    # ===== Avatar 系统保留参数 (Read-only) =====
    "Avatar_VRCEmote": {
        "address": "/avatar/parameters/VRCEmote",
        "type": "Int",
        "min": 1,
        "max": 16,
        "category": "avatar",
        "display_name": "表情动作",
        "description": "VRChat默认表情"
    },
    "Avatar_VRCFaceBlendV": {
        "address": "/avatar/parameters/VRCFaceBlendV",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "面部表情V",
        "description": "面部表情垂直混合"
    },
    "Avatar_VRCFaceBlendH": {
        "address": "/avatar/parameters/VRCFaceBlendH",
        "type": "Float",
        "min": -1.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "面部表情H",
        "description": "面部表情水平混合"
    },
    "Avatar_GestureRight": {
        "address": "/avatar/parameters/GestureRight",
        "type": "Int",
        "min": 0,
        "max": 7,
        "category": "avatar",
        "display_name": "右手手势",
        "description": "右手手势状态"
    },
    "Avatar_GestureLeft": {
        "address": "/avatar/parameters/GestureLeft",
        "type": "Int",
        "min": 0,
        "max": 7,
        "category": "avatar",
        "display_name": "左手手势",
        "description": "左手手势状态"
    },
    "Avatar_GestureRightWeight": {
        "address": "/avatar/parameters/GestureRightWeight",
        "type": "Float",
        "min": 0.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "右手手势权重",
        "description": "右手手势强度"
    },
    "Avatar_GestureLeftWeight": {
        "address": "/avatar/parameters/GestureLeftWeight",
        "type": "Float",
        "min": 0.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "左手手势权重",
        "description": "左手手势强度"
    },
    "Avatar_ScaleModified": {
        "address": "/avatar/parameters/ScaleModified",
        "type": "Bool",
        "category": "avatar",
        "display_name": "缩放修改",
        "description": "身形缩放已修改"
    },
    "Avatar_ScaleFactor": {
        "address": "/avatar/parameters/ScaleFactor",
        "type": "Float",
        "min": 0.1,
        "max": 10.0,
        "category": "avatar",
        "display_name": "缩放因子",
        "description": "当前身高/默认身高"
    },
    "Avatar_ScaleFactorInverse": {
        "address": "/avatar/parameters/ScaleFactorInverse",
        "type": "Float",
        "min": 0.1,
        "max": 10.0,
        "category": "avatar",
        "display_name": "缩放因子逆",
        "description": "默认身高/当前身高"
    },
    "Avatar_EyeHeightAsMeters": {
        "address": "/avatar/parameters/EyeHeightAsMeters",
        "type": "Float",
        "min": 0.2,
        "max": 5.0,
        "category": "avatar",
        "display_name": "眼高米",
        "description": "眼睛高度（米）"
    },
    "Avatar_EyeHeightAsPercent": {
        "address": "/avatar/parameters/EyeHeightAsPercent",
        "type": "Float",
        "min": 0.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "眼高百分比",
        "description": "眼睛高度百分比"
    },
    "Avatar_Viseme": {
        "address": "/avatar/parameters/Viseme",
        "type": "Int",
        "min": 0,
        "max": 14,
        "category": "avatar",
        "display_name": "视位",
        "description": "口型视位"
    },
    "Avatar_Voice": {
        "address": "/avatar/parameters/Voice",
        "type": "Float",
        "min": 0.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "音量",
        "description": "麦克风音量"
    },
    "Avatar_Earmuffs": {
        "address": "/avatar/parameters/Earmuffs",
        "type": "Bool",
        "category": "avatar",
        "display_name": "耳罩模式",
        "description": "耳罩模式开启"
    },
    "Avatar_MuteSelf": {
        "address": "/avatar/parameters/MuteSelf",
        "type": "Bool",
        "category": "avatar",
        "display_name": "自我静音",
        "description": "自我静音状态"
    },
    "Avatar_AFK": {
        "address": "/avatar/parameters/AFK",
        "type": "Bool",
        "category": "avatar",
        "display_name": "AFK状态",
        "description": "离开状态"
    },
    "Avatar_InStation": {
        "address": "/avatar/parameters/InStation",
        "type": "Bool",
        "category": "avatar",
        "display_name": "在座位上",
        "description": "处于座位中"
    },
    "Avatar_Seated": {
        "address": "/avatar/parameters/Seated",
        "type": "Bool",
        "category": "avatar",
        "display_name": "坐着",
        "description": "坐姿状态"
    },
    "Avatar_VRMode": {
        "address": "/avatar/parameters/VRMode",
        "type": "Int",
        "min": 0,
        "max": 1,
        "category": "avatar",
        "display_name": "VR模式",
        "description": "VR/桌面模式"
    },
    "Avatar_TrackingType": {
        "address": "/avatar/parameters/TrackingType",
        "type": "Int",
        "min": 0,
        "max": 4,
        "category": "avatar",
        "display_name": "追踪类型",
        "description": "追踪点数量"
    },
    "Avatar_Grounded": {
        "address": "/avatar/parameters/Grounded",
        "type": "Bool",
        "category": "avatar",
        "display_name": "着地",
        "description": "脚部接触地面"
    },
    "Avatar_Upright": {
        "address": "/avatar/parameters/Upright",
        "type": "Float",
        "min": 0.0,
        "max": 1.0,
        "category": "avatar",
        "display_name": "直立度",
        "description": "身体直立程度"
    },
    "Avatar_AngularY": {
        "address": "/avatar/parameters/AngularY",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "avatar",
        "display_name": "Y轴角速度",
        "description": "Y轴旋转角速度"
    },
    "Avatar_VelocityX": {
        "address": "/avatar/parameters/VelocityX",
        "type": "Float",
        "min": -5.0,
        "max": 5.0,
        "category": "avatar",
        "display_name": "X轴速度",
        "description": "横向移动速度"
    },
    "Avatar_VelocityY": {
        "address": "/avatar/parameters/VelocityY",
        "type": "Float",
        "min": -5.0,
        "max": 5.0,
        "category": "avatar",
        "display_name": "Y轴速度",
        "description": "垂直移动速度"
    },
    "Avatar_VelocityZ": {
        "address": "/avatar/parameters/VelocityZ",
        "type": "Float",
        "min": -5.0,
        "max": 5.0,
        "category": "avatar",
        "display_name": "Z轴速度",
        "description": "纵向移动速度"
    },
    "Avatar_VelocityMagnitude": {
        "address": "/avatar/parameters/VelocityMagnitude",
        "type": "Float",
        "min": 0.0,
        "max": 10.0,
        "category": "avatar",
        "display_name": "速度大小",
        "description": "总速度大小"
    },
    "Avatar_PreviewMode": {
        "address": "/avatar/parameters/PreviewMode",
        "type": "Int",
        "min": 0,
        "max": 1,
        "category": "avatar",
        "display_name": "预览模式",
        "description": "菜单预览模式"
    },
    "Avatar_IsOnFriendsList": {
        "address": "/avatar/parameters/IsOnFriendsList",
        "type": "Bool",
        "category": "avatar",
        "display_name": "好友列表",
        "description": "在好友列表中"
    },
    "Avatar_IsAnimatorEnabled": {
        "address": "/avatar/parameters/IsAnimatorEnabled",
        "type": "Bool",
        "category": "avatar",
        "display_name": "动画器启用",
        "description": "动画器已启用"
    },

    # ===== System (Read-only) =====
    "System_AvatarID": {
        "address": "/avatar/change",
        "type": "String",
        "category": "system",
        "display_name": "角色ID",
        "description": "当前角色ID"
    },

    # ===== Tracking (Read-only) =====
    "Tracking_HeadPosX": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "头部位置X",
        "index": 0,
        "description": "头部X轴位置"
    },
    "Tracking_HeadPosY": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "头部位置Y",
        "index": 1,
        "description": "头部Y轴位置"
    },
    "Tracking_HeadPosZ": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "头部位置Z",
        "index": 2,
        "description": "头部Z轴位置"
    },
    "Tracking_HeadRotX": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "头部旋转X",
        "index": 3,
        "description": "头部X轴旋转"
    },
    "Tracking_HeadRotY": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "头部旋转Y",
        "index": 4,
        "description": "头部Y轴旋转"
    },
    "Tracking_HeadRotZ": {
        "address": "/tracking/vrsystem/head/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "头部旋转Z",
        "index": 5,
        "description": "头部Z轴旋转"
    },
    "Tracking_LeftWristPosX": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "左手腕位置X",
        "index": 0,
        "description": "左手腕X轴位置"
    },
    "Tracking_LeftWristPosY": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "左手腕位置Y",
        "index": 1,
        "description": "左手腕Y轴位置"
    },
    "Tracking_LeftWristPosZ": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "左手腕位置Z",
        "index": 2,
        "description": "左手腕Z轴位置"
    },
    "Tracking_LeftWristRotX": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "左手腕旋转X",
        "index": 3,
        "description": "左手腕X轴旋转"
    },
    "Tracking_LeftWristRotY": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "左手腕旋转Y",
        "index": 4,
        "description": "左手腕Y轴旋转"
    },
    "Tracking_LeftWristRotZ": {
        "address": "/tracking/vrsystem/leftwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "左手腕旋转Z",
        "index": 5,
        "description": "左手腕Z轴旋转"
    },
    "Tracking_RightWristPosX": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "右手腕位置X",
        "index": 0,
        "description": "右手腕X轴位置"
    },
    "Tracking_RightWristPosY": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "右手腕位置Y",
        "index": 1,
        "description": "右手腕Y轴位置"
    },
    "Tracking_RightWristPosZ": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -10.0,
        "max": 10.0,
        "category": "tracking",
        "display_name": "右手腕位置Z",
        "index": 2,
        "description": "右手腕Z轴位置"
    },
    "Tracking_RightWristRotX": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "右手腕旋转X",
        "index": 3,
        "description": "右手腕X轴旋转"
    },
    "Tracking_RightWristRotY": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "右手腕旋转Y",
        "index": 4,
        "description": "右手腕Y轴旋转"
    },
    "Tracking_RightWristRotZ": {
        "address": "/tracking/vrsystem/rightwrist/pose",
        "type": "Float",
        "min": -180.0,
        "max": 180.0,
        "category": "tracking",
        "display_name": "右手腕旋转Z",
        "index": 5,
        "description": "右手腕Z轴旋转"
    },

    # ===== Dolly (Write-only) =====
    "Dolly_Play": {
        "address": "/dolly/Play",
        "type": "Bool",
        "category": "dolly",
        "display_name": "播放轨道",
        "description": "播放轨道动画"
    },
    "Dolly_PlayDelayed": {
        "address": "/dolly/PlayDelayed",
        "type": "Float",
        "min": 0.0,
        "max": 60.0,
        "category": "dolly",
        "display_name": "延时播放",
        "description": "延时播放轨道"
    },
}


class AvatarParameterLoader:
    """角色参数加载器 - 处理动态加载角色自定义参数
    
    当VRChat切换角色时，自动从本地OSC目录加载对应角色的JSON配置文件，
    提取自定义参数并实时更新到系统中。
    """
    
    def __init__(self, controller):
        """初始化角色参数加载器
        
        参数:
            controller: VRChatController实例，用于回调和参数管理
        """
        self.controller = controller
        self.custom_params: Dict[str, Parameter] = {}
        self.current_avatar_id: Optional[str] = None
        self.current_avatar_name: str = ""
    
    def _get_vrchat_osc_path(self) -> Optional[str]:
        """自动扫描获取 VRChat OSC 路径
        
        通过环境变量获取用户目录，扫描找到 usr_* 文件夹。
        
        返回:
            Avatars 目录路径，如果未找到则返回 None
        """
        try:
            # 获取用户主目录，构建 LocalLow 路径
            # VRChat OSC 文件存放在 AppData/LocalLow 而非 Local
            user_profile = os.environ.get('USERPROFILE')
            if not user_profile:
                print("[AvatarLoader] USERPROFILE environment variable not found")
                return None
            
            # 基础 OSC 路径 (LocalLow 目录)
            osc_base = os.path.join(user_profile, 'AppData', 'LocalLow', 'VRChat', 'VRChat', 'OSC')
            if not os.path.exists(osc_base):
                print(f"[AvatarLoader] OSC directory not found: {osc_base}")
                return None
            
            # 扫描 usr_* 文件夹
            usr_dirs = [d for d in os.listdir(osc_base) 
                       if d.startswith('usr_') and os.path.isdir(os.path.join(osc_base, d))]
            
            if not usr_dirs:
                print(f"[AvatarLoader] No usr_* directory found in {osc_base}")
                return None
            
            # 使用第一个找到的 usr 目录
            usr_dir = usr_dirs[0]
            avatars_path = os.path.join(osc_base, usr_dir, 'Avatars')
            
            if not os.path.exists(avatars_path):
                print(f"[AvatarLoader] Avatars directory not found: {avatars_path}")
                return None
            
            return avatars_path
            
        except Exception as e:
            print(f"[AvatarLoader] Error finding OSC path: {e}")
            return None
    
    def _get_default_range(self, param_type: str) -> tuple:
        """获取参数类型的默认数值范围
        
        参数:
            param_type: 参数类型 (Bool, Int, Float)
            
        返回:
            (min_val, max_val) 元组
        """
        if param_type == "Bool":
            return 0, 1
        elif param_type == "Int":
            return 0, 20
        else:  # Float
            return 0.0, 1.0
    
    def _parse_avatar_json(self, file_path: str) -> Optional[Dict]:
        """解析角色 JSON 文件
        
        参数:
            file_path: JSON 文件完整路径
            
        返回:
            包含 name 和 params 的字典，解析失败返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            avatar_name = data.get('name', 'Unknown')
            parameters = data.get('parameters', [])
            
            parsed_params = {}
            
            for param_def in parameters:
                name = param_def.get('name')
                if not name:
                    continue
                
                # 检查 input/output 定义
                has_input = 'input' in param_def
                has_output = 'output' in param_def
                
                if not has_input and not has_output:
                    continue
                
                # 获取 address 和 type（优先使用 input）
                if has_input:
                    address = param_def['input']['address']
                    param_type = param_def['input']['type']
                else:
                    address = param_def['output']['address']
                    param_type = param_def['output']['type']
                
                min_val, max_val = self._get_default_range(param_type)
                
                # 创建参数对象
                param = Parameter(
                    name=f"Custom_{name}",  # 添加前缀避免与系统参数冲突
                    address=address,
                    param_type=param_type,
                    min_val=min_val,
                    max_val=max_val,
                    is_input=has_input,
                    is_output=has_output,
                    category="avatar",  # 使用 avatar 类别以便接收 OSC 消息
                    description=f"自定义参数: {avatar_name}",
                    display_name=name
                )
                
                parsed_params[param.name] = param
            
            return {
                'name': avatar_name,
                'params': parsed_params
            }
            
        except Exception as e:
            print(f"[AvatarLoader] Error parsing JSON: {e}")
            return None
    
    def _filter_existing_addresses(self, params: Dict[str, Parameter]) -> Dict[str, Parameter]:
        """过滤掉系统中已存在的 address
        
        参数:
            params: 待过滤的参数字典
            
        返回:
            过滤后的参数字典
        """
        # 获取系统所有已存在的 address
        existing_addresses = {p.address for p in self.controller.parameters.values()}
        
        filtered = {}
        for name, param in params.items():
            if param.address in existing_addresses:
                print(f"[AvatarLoader] Skipping existing address: {param.address}")
                continue
            filtered[name] = param
        
        return filtered
    
    async def load_avatar_params(self, avatar_id: str) -> bool:
        """加载指定角色的自定义参数
        
        1. 清空现有自定义参数
        2. 查找 JSON 文件
        3. 解析并过滤参数
        4. 添加到系统并广播给前端
        
        参数:
            avatar_id: 角色ID
            
        返回:
            是否成功加载参数
        """
        if avatar_id == self.current_avatar_id:
            return True  # 同一角色，无需重新加载
        
        # 1. 清空现有自定义参数
        await self.clear_custom_params()
        
        self.current_avatar_id = avatar_id
        
        # 2. 查找 JSON 文件
        avatars_path = self._get_vrchat_osc_path()
        if not avatars_path:
            return False
        
        json_file = os.path.join(avatars_path, f"{avatar_id}.json")
        if not os.path.exists(json_file):
            print(f"[AvatarLoader] Avatar JSON not found: {json_file}")
            return False
        
        print(f"[AvatarLoader] Loading avatar params from: {json_file}")
        
        # 3. 解析 JSON
        result = self._parse_avatar_json(json_file)
        if not result:
            return False
        
        self.current_avatar_name = result['name']
        raw_params = result['params']
        
        # 4. 过滤已存在的 address
        self.custom_params = self._filter_existing_addresses(raw_params)
        
        if not self.custom_params:
            print("[AvatarLoader] No new custom parameters found")
            return False
        
        # 5. 添加到系统参数
        self.controller.parameters.update(self.custom_params)
        
        print(f"[AvatarLoader] Loaded {len(self.custom_params)} custom parameters for '{self.current_avatar_name}'")
        
        # 6. 广播给前端
        param_list = []
        for param in self.custom_params.values():
            param_list.append({
                "name": param.name,
                "type": param.param_type,
                "address": param.address,
                "min": param.min_val,
                "max": param.max_val,
                "isInput": param.is_input,
                "isOutput": param.is_output,
                "value": param.value,
                "category": param.category,
                "displayName": param.display_name,
                "description": param.description
            })
        
        await self.controller.broadcast({
            "type": "custom_params",
            "avatarName": self.current_avatar_name,
            "parameters": param_list
        })
        
        return True
    
    async def clear_custom_params(self):
        """清空当前自定义参数并通知前端"""
        if not self.custom_params:
            return
        
        # 从系统参数中移除
        for name in self.custom_params:
            if name in self.controller.parameters:
                del self.controller.parameters[name]
        
        # 通知前端清空
        await self.controller.broadcast({
            "type": "clear_custom_params"
        })
        
        self.custom_params.clear()
        print("[AvatarLoader] Cleared custom parameters")


def load_parameters() -> Dict[str, Parameter]:
    """从 WIKI_PARAMETERS 加载参数
    
    如需扩展自定义参数，在此函数中添加即可
    """
    parameters = {}
    
    for name, config in WIKI_PARAMETERS.items():
        category = config.get("category", "other")
        
        # 根据类别确定输入/输出属性
        is_input = category in ("input", "chatbox", "camera", "system", "dolly")
        is_output = category in ("camera", "system", "tracking", "avatar")
        
        param = Parameter(
            name=name,
            address=config["address"],
            param_type=config["type"],
            min_val=config.get("min", 0.0),
            max_val=config.get("max", 1.0),
            is_input=is_input,
            is_output=is_output,
            category=category,
            description=config.get("description", ""),
            display_name=config.get("display_name", name)
        )
        parameters[name] = param
    
    print(f"[Config] Loaded {len(parameters)} parameters from WIKI_PARAMETERS")
    return parameters


class OSCManager:
    """OSC管理器
    
    负责VRChat OSC通信的客户端和服务器端管理。
    处理OSC消息的发送、接收和分发。
    """
    def __init__(self, controller):
        """初始化OSC管理器
        
        参数:
            controller: VRChatController实例，用于回调
        """
        self.controller = controller
        self.client: Optional[SimpleUDPClient] = None
        self.server: Optional[AsyncIOOSCUDPServer] = None
        self.dispatcher = Dispatcher()
        self.transport = None
        self.message_queue = asyncio.Queue()
        self._running = False

    def setup(self):
        """初始化OSC客户端和服务器
        
        创建OSC客户端用于发送消息到VRChat，
        设置OSC消息处理器用于接收来自VRChat的消息。
        """
        self.client = SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)

        # Set up OSC message handlers
        self.dispatcher.map("/avatar/parameters/*", self._handle_avatar_messages)
        self.dispatcher.map("/avatar/change", self._handle_avatar_change)
        self.dispatcher.map("/usercamera/*", self._handle_camera_messages)
        self.dispatcher.map("/tracking/vrsystem/*/pose", self._handle_tracking_messages)
        self.dispatcher.set_default_handler(self._handle_unknown_message)

    def _handle_avatar_messages(self, address: str, *args):
        """处理角色参数消息
        
        将接收到的角色参数消息放入消息队列，供后续处理。
        """
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
        """处理角色切换消息
        
        当VRChat切换角色时接收到的消息，记录角色ID并放入消息队列。
        """
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
        """处理相机参数消息
        
        将接收到的相机参数消息放入消息队列，供后续处理。
        """
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
        """处理追踪消息（6个浮点数值）
        
        处理VR追踪数据，包含位置和旋转信息。
        """
        if len(args) < 6:
            return
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                self.message_queue.put_nowait, ("tracking", address, list(args[:6]))
            )
        except:
            pass

    def _handle_unknown_message(self, address: str, *args):
        """处理未知OSC消息
        
        记录未匹配到处理器的OSC消息，用于调试。
        """
        if args:
            print(f"[OSC] Unknown message: {address} {args}")

    async def process_messages(self):
        """处理消息队列
        
        从消息队列中获取OSC消息，找到对应的参数并更新其值，
        然后广播给所有WebSocket客户端。
        """
        while self._running:
            try:
                category, address, value = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.1
                )

                # Handle avatar change event
                if category == "system" and address == "/avatar/change":
                    avatar_id = str(value)
                    if self.controller.avatar_loader:
                        await self.controller.avatar_loader.load_avatar_params(avatar_id)
                    # 继续更新 System_AvatarID 参数的值，而不是跳过

                # Find corresponding parameter
                for name, param in self.controller.parameters.items():
                    if param.category != category:
                        continue

                    # Special handling for tracking (multi-value)
                    if category == "tracking" and isinstance(value, list):
                        if param.address == address:
                            idx = WIKI_PARAMETERS.get(name, {}).get("index", 0)
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
        """启动OSC接收服务器
        
        创建OSC UDP服务器端点，开始监听来自VRChat的消息。
        """
        loop = asyncio.get_event_loop()
        self.server = AsyncIOOSCUDPServer(
            ("0.0.0.0", OSC_RECEIVE_PORT),
            self.dispatcher,
            loop
        )
        self.transport, protocol = await self.server.create_serve_endpoint()
        self._running = True

        asyncio.create_task(self.process_messages())

        print(f"[OSC] Server listening on port {OSC_RECEIVE_PORT}")

    async def stop_server(self):
        """停止OSC服务器
        
        关闭OSC服务器传输，停止消息处理循环。
        """
        self._running = False
        if self.transport:
            self.transport.close()

    def send(self, address: str, value: Any):
        """发送OSC消息到VRChat
        
        通过OSC客户端向VRChat发送参数值。
        """
        if self.client:
            self.client.send_message(address, value)
            print(f"[OSC] Sent: {address} = {value}")


class VRChatController:
    """VRChat OSC控制器
    
    主控制器类，管理参数提供器、OSC通信和WebSocket连接。
    协调参数加载、消息处理和前端通信。
    """
    def __init__(self):
        """初始化VRChat OSC控制器
        
        初始化参数字典、WebSocket连接集合和OSC管理器。
        """
        self.parameters: Dict[str, Parameter] = {}
        self.websockets: set = set()
        self.osc = OSCManager(self)
        self.avatar_loader: Optional[AvatarParameterLoader] = None

    def load_config(self):
        """加载参数配置"""
        self.parameters = load_parameters()
        self.avatar_loader = AvatarParameterLoader(self)
        print(f"[Config] Total parameters loaded: {len(self.parameters)}")

    def get_parameter_list(self) -> List[Dict]:
        """获取前端参数列表
        
        将参数对象转换为前端可用的字典格式。
        注意：此方法只返回系统参数，不包含自定义参数。
        自定义参数通过单独的 custom_params 消息发送。
        
        返回:
            参数字典列表，包含所有前端需要的字段
        """
        result = []
        for name, param in self.parameters.items():
            # 过滤自定义参数（名称以 Custom_ 开头）
            if name.startswith("Custom_"):
                continue
            result.append({
                "name": name,
                "type": param.param_type,
                "address": param.address,
                "min": param.min_val,
                "max": param.max_val,
                "isInput": param.is_input,
                "isOutput": param.is_output,
                "value": param.value,
                "category": param.category,
                "displayName": param.display_name,
                "description": param.description
            })
        return result

    async def broadcast(self, message: Dict):
        """广播消息到所有WebSocket客户端
        
        将消息发送给所有连接的WebSocket客户端，
        自动处理断开连接的客户端。
        """
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
        """处理WebSocket连接
        
        建立WebSocket连接，发送初始参数列表，
        并处理来自前端的消息。
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        print(f"[WebSocket] Client connected")
        self.websockets.add(ws)

        # Send initial parameter list
        await ws.send_json({
            "type": "init",
            "parameters": self.get_parameter_list()
        })

        # 如果已有自定义参数，发送给新连接的前端
        if self.avatar_loader and self.avatar_loader.custom_params:
            param_list = []
            for param in self.avatar_loader.custom_params.values():
                param_list.append({
                    "name": param.name,
                    "type": param.param_type,
                    "address": param.address,
                    "min": param.min_val,
                    "max": param.max_val,
                    "isInput": param.is_input,
                    "isOutput": param.is_output,
                    "value": param.value,
                    "category": param.category,
                    "displayName": param.display_name,
                    "description": param.description
                })
            
            await ws.send_json({
                "type": "custom_params",
                "avatarName": self.avatar_loader.current_avatar_name,
                "parameters": param_list
            })
            print(f"[WebSocket] Sent {len(param_list)} custom params to new client")

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
        """处理来自前端的消息
        
        解析前端发送的消息，根据消息类型执行相应操作。
        """
        msg_type = data.get("type")

        if msg_type == "set":
            name = data.get("name")
            value = data.get("value")

            if name in self.parameters:
                param = self.parameters[name]
                param.value = value

                # Convert value based on parameter type
                send_value = value
                if param.param_type == "Float":
                    send_value = float(value)
                elif param.param_type == "Int":
                    send_value = int(value)
                elif param.param_type == "Bool":
                    send_value = bool(value)

                # Send to VRChat
                self.osc.send(param.address, send_value)

                # Broadcast to other clients
                await self.broadcast({
                    "type": "input",
                    "name": name,
                    "value": value,
                    "category": param.category
                })

        elif msg_type == "chatbox":
            text = data.get("text", "")
            send_immediately = data.get("send", True)
            notification = data.get("notification", True)

            if self.osc.client:
                self.osc.client.send_message("/chatbox/input", [text, send_immediately, notification])
                print(f"[OSC] Chatbox: {text}")


controller = VRChatController()


async def index_handler(request):
    """处理首页请求
    
    返回静态HTML页面。
    """
    return web.FileResponse('./static/index.html')


async def init_app():
    """初始化应用程序
    
    加载配置，启动OSC服务器，
    并创建Web应用路由。
    """
    controller.load_config()

    controller.osc.setup()
    await controller.osc.start_server()

    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', controller.handle_websocket)
    app.router.add_static('/static/', path='./static', name='static')

    return app


async def main():
    """主函数
    
    启动Web服务器和OSC通信，等待用户中断。
    """
    app = await init_app()

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()

    print(f"[Web] Server started at http://localhost:{WEB_PORT}")
    print(f"[OSC] Sending to {OSC_SEND_IP}:{OSC_SEND_PORT}")
    print(f"[OSC] Receiving on port {OSC_RECEIVE_PORT}")
    print("\nPress Ctrl+C to stop\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        await controller.osc.stop_server()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())