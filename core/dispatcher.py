from typing import Dict, List, Callable, Any
from .events import Event, EventType


class EventDispatcher:
    """事件分发器，管理事件的发布和订阅"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], Any]]] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """订阅特定类型的事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """取消订阅特定类型的事件"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
    
    def publish(self, event: Event):
        """发布事件给所有订阅者"""
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    # 记录错误但不中断事件处理链
                    print(f"处理事件 {event.type.value} 时发生错误: {e}")
    
    def publish_async(self, event: Event):
        """异步发布事件（需要在异步环境中运行）"""
        import asyncio
        
        async def async_publish():
            if event.type in self._subscribers:
                for handler in self._subscribers[event.type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        print(f"异步处理事件 {event.type.value} 时发生错误: {e}")
        
        asyncio.create_task(async_publish())
    
    def get_subscribers(self, event_type: EventType) -> List[Callable[[Event], Any]]:
        """获取特定事件类型的所有订阅者"""
        return self._subscribers.get(event_type, [])
    
    def clear_subscribers(self, event_type: EventType = None):
        """清除所有订阅者或特定事件类型的订阅者"""
        if event_type:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
        else:
            self._subscribers.clear()
