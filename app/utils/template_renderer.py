"""
模板渲染器：提供用于渲染助手网页和其他界面组件的HTML模板功能
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import settings

# 初始化Jinja2环境
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_assistant_page(assistant: Any) -> str:
    """
    渲染用于与助手交互的HTML页面
    
    参数:
        assistant: 来自数据库的助手对象
        
    返回:
        渲染后的HTML内容
    """
    # 检查模板目录是否存在，如果不存在则创建
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        
        # 如果默认模板不存在则创建
        template_path = os.path.join(template_dir, "assistant.html")
        if not os.path.exists(template_path):
            with open(template_path, "w") as f:
                f.write(DEFAULT_ASSISTANT_TEMPLATE)
    
    # 获取模板
    template = env.get_template("assistant.html")
    
    # 提取助手功能
    capabilities = assistant.capabilities or []
    has_multimodal = "multimodal" in capabilities
    has_voice = "voice" in capabilities
    
    # 准备上下文数据
    context = {
        "assistant": {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "model": assistant.model,
            "capabilities": capabilities,
            "has_multimodal": has_multimodal,
            "has_voice": has_voice,
            "created_at": assistant.created_at.isoformat() if hasattr(assistant, 'created_at') else datetime.now().isoformat(),
        },
        "api_base_url": f"{settings.BASE_URL}/api/v1/assistants",
        "static_url": f"{settings.BASE_URL}/static",
        "config": {
            "streaming": True,
            "max_tokens": 2000,
            "temperature": 0.7
        }
    }
    
    # 渲染模板
    return template.render(**context)


def render_conversation_export(conversation: Any, messages: List[Any]) -> str:
    """
    将对话导出为HTML格式
    
    参数:
        conversation: 来自数据库的对话对象
        messages: 消息对象列表
        
    返回:
        渲染后的HTML内容
    """
    # 获取模板
    template_path = os.path.join(template_dir, "conversation_export.html")
    if not os.path.exists(template_path):
        with open(template_path, "w") as f:
            f.write(DEFAULT_EXPORT_TEMPLATE)
    
    template = env.get_template("conversation_export.html")
    
    # 格式化消息
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if hasattr(msg, 'created_at') else "",
        })
    
    # 准备上下文数据
    context = {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if hasattr(conversation, 'created_at') else "",
        },
        "assistant": {
            "id": conversation.assistant_id,
            "name": getattr(conversation, "assistant_name", "Assistant"),
        },
        "messages": formatted_messages,
        "export_date": datetime.now().isoformat(),
        "static_url": f"{settings.BASE_URL}/static"
    }
    
    # 渲染模板
    return template.render(**context)


# 默认助手模板
DEFAULT_ASSISTANT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ assistant.name }} - AI助手</title>
    <style>
        :root {
            --primary-color: #3a6ea5;
            --secondary-color: #e3f2fd;
            --accent-color: #ff6b6b;
            --text-color: #333;
            --light-text: #666;
            --background: #fff;
            --chat-user-bg: #e3f2fd;
            --chat-assistant-bg: #f5f5f5;
            --border-color: #ddd;
            --shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        
        header {
            background-color: var(--primary-color);
            color: white;
            padding: 1rem;
            text-align: center;
            box-shadow: var(--shadow);
        }
        
        h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        
        .description {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-top: 0.5rem;
        }
        
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 1000px;
            margin: 0 auto;
            padding: 1rem;
            width: 100%;
            box-sizing: border-box;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            background-color: white;
            box-shadow: var(--shadow);
            min-height: 400px;
            max-height: 60vh;
        }
        
        .message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border-radius: 0.5rem;
            max-width: 80%;
        }
        
        .user {
            background-color: var(--chat-user-bg);
            align-self: flex-end;
            margin-left: auto;
        }
        
        .assistant {
            background-color: var(--chat-assistant-bg);
            align-self: flex-start;
            margin-right: auto;
        }
        
        .message-container {
            display: flex;
            flex-direction: column;
        }
        
        .input-container {
            display: flex;
            margin-top: 1rem;
            gap: 0.5rem;
        }
        
        #user-input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 0.25rem;
            font-size: 1rem;
        }
        
        button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.25rem;
            padding: 0.75rem 1rem;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        
        button:hover {
            background-color: #2a5a8f;
        }
        
        button:disabled {
            background-color: var(--light-text);
            cursor: not-allowed;
        }
        
        .controls {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        
        .file-upload {
            display: none;
        }
        
        .upload-label {
            display: inline-flex;
            align-items: center;
            background-color: var(--secondary-color);
            color: var(--primary-color);
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.9rem;
        }
        
        .upload-label:hover {
            background-color: #d1e4f7;
        }
        
        footer {
            text-align: center;
            padding: 1rem;
            background-color: var(--secondary-color);
            color: var(--light-text);
            font-size: 0.8rem;
        }
        
        .thinking {
            display: flex;
            align-items: center;
            padding: 0.5rem;
            color: var(--light-text);
        }
        
        .dot-flashing {
            position: relative;
            width: 10px;
            height: 10px;
            border-radius: 5px;
            background-color: var(--light-text);
            color: var(--light-text);
            animation: dot-flashing 1s infinite linear alternate;
            animation-delay: 0.5s;
            margin-right: 20px;
        }
        
        .dot-flashing::before, .dot-flashing::after {
            content: '';
            display: inline-block;
            position: absolute;
            top: 0;
        }
        
        .dot-flashing::before {
            left: -15px;
            width: 10px;
            height: 10px;
            border-radius: 5px;
            background-color: var(--light-text);
            color: var(--light-text);
            animation: dot-flashing 1s infinite alternate;
            animation-delay: 0s;
        }
        
        .dot-flashing::after {
            left: 15px;
            width: 10px;
            height: 10px;
            border-radius: 5px;
            background-color: var(--light-text);
            color: var(--light-text);
            animation: dot-flashing 1s infinite alternate;
            animation-delay: 1s;
        }
        
        @keyframes dot-flashing {
            0% {
                background-color: var(--light-text);
            }
            50%, 100% {
                background-color: rgba(152, 128, 255, 0.2);
            }
        }
        
        @media (max-width: 768px) {
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>{{ assistant.name }}</h1>
        <div class="description">{{ assistant.description }}</div>
    </header>
    
    <main>
        <div class="controls">
            <div>
                {% if assistant.has_multimodal %}
                <label class="upload-label" for="file-upload">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M4.502 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3"/>
                        <path d="M14.002 13a2 2 0 0 1-2 2h-10a2 2 0 0 1-2-2V5A2 2 0 0 1 2 3a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v8a2 2 0 0 1-1.998 2M14 2H4a1 1 0 0 0-1 1h9.002a2 2 0 0 1 2 2v7A1 1 0 0 0 15 11V3a1 1 0 0 0-1-1M2.002 4a1 1 0 0 0-1 1v8l2.646-2.354a.5.5 0 0 1 .63-.062l2.66 1.773 3.71-3.71a.5.5 0 0 1 .577-.094l1.777 1.947V5a1 1 0 0 0-1-1h-10"/>
                    </svg>
                    上传图片
                </label>
                <input id="file-upload" class="file-upload" type="file" accept="image/*">
                {% endif %}
            </div>
            
            <button id="new-chat-btn">新建聊天</button>
        </div>
        
        <div id="chat-container" class="chat-container">
            <div class="message-container">
                <div class="message assistant">
                    <p>您好！我是{{ assistant.name }}。我可以如何帮助您今天？</p>
                </div>
            </div>
        </div>
        
        <div class="input-container">
            <input type="text" id="user-input" placeholder="输入您的消息..." aria-label="消息输入">
            {% if assistant.has_voice %}
            <button id="voice-btn" title="语音输入">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 8a3 3 0 0 0 3-3V3a3 3 0 0 0-6 0v2a3 3 0 0 0 3 3"/>
                    <path d="M5 4.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5"/>
                </svg>
            </button>
            {% endif %}
            <button id="send-btn">发送</button>
        </div>
    </main>
    
    <footer>
        <p>由知识问答系统提供支持 | 模型：{{ assistant.model }}</p>
    </footer>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const chatContainer = document.getElementById('chat-container');
            const userInput = document.getElementById('user-input');
            const sendButton = document.getElementById('send-btn');
            const newChatButton = document.getElementById('new-chat-btn');
            {% if assistant.has_voice %}
            const voiceButton = document.getElementById('voice-btn');
            {% endif %}
            {% if assistant.has_multimodal %}
            const fileUpload = document.getElementById('file-upload');
            {% endif %}
            
            let conversationId = null;
            let waitingForResponse = false;
            let uploadedImages = [];
            
            // 函数添加消息到聊天
            function addMessage(content, role) {
                const messageContainer = document.createElement('div');
                messageContainer.className = 'message-container';
                
                const messageElement = document.createElement('div');
                messageElement.className = `message ${role}`;
                messageElement.innerHTML = `<p>${content}</p>`;
                
                messageContainer.appendChild(messageElement);
                chatContainer.appendChild(messageContainer);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            // 函数添加思考指示器
            function addThinkingIndicator() {
                const thinkingContainer = document.createElement('div');
                thinkingContainer.className = 'message-container thinking-container';
                
                const thinkingElement = document.createElement('div');
                thinkingElement.className = 'message assistant thinking';
                thinkingElement.innerHTML = `
                    <div class="dot-flashing"></div>
                    <span>思考中...</span>
                `;
                
                thinkingContainer.appendChild(thinkingElement);
                chatContainer.appendChild(thinkingContainer);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                return thinkingContainer;
            }
            
            // 函数发送消息到助手
            async function sendMessage() {
                const message = userInput.value.trim();
                if (message === '' && uploadedImages.length === 0) return;
                
                if (waitingForResponse) return;
                waitingForResponse = true;
                
                // 添加用户消息到聊天
                addMessage(message, 'user');
                
                // 清空输入
                userInput.value = '';
                
                // 准备请求正文
                let requestBody = {
                    messages: []
                };
                
                // 添加系统消息如果这是一个新对话
                if (!conversationId) {
                    requestBody.messages.push({
                        role: 'system',
                        content: '您是{{ assistant.name }}, 一个有用的AI助手。'
                    });
                } else {
                    requestBody.conversation_id = conversationId;
                }
                
                // 添加用户消息
                {% if assistant.has_multimodal %}
                if (uploadedImages.length > 0) {
                    // 格式化为多模态内容
                    const content = [];
                    
                    if (message) {
                        content.push({
                            type: 'text',
                            text: message
                        });
                    }
                    
                    for (const image of uploadedImages) {
                        content.push({
                            type: 'image_url',
                            image_url: {
                                url: image
                            }
                        });
                    }
                    
                    requestBody.messages.push({
                        role: 'user',
                        content: content
                    });
                    
                    // 清空上传的图片
                    uploadedImages = [];
                } else {
                    requestBody.messages.push({
                        role: 'user',
                        content: message
                    });
                }
                {% else %}
                requestBody.messages.push({
                    role: 'user',
                    content: message
                });
                {% endif %}
                
                // 添加思考指示器
                const thinkingContainer = addThinkingIndicator();
                
                try {
                    // 发送请求到API
                    const response = await fetch('{{ api_base_url }}/{{ assistant.id }}/chat/completions', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    
                    const data = await response.json();
                    
                    if (!data.message_id) {
                        throw new Error('无效的服务器响应');
                    }
                    
                    // 保存对话ID
                    if (data.conversation_id) {
                        conversationId = data.conversation_id;
                    }
                    
                    // 轮询响应
                    await pollForResponse(data.message_id, thinkingContainer);
                    
                } catch (error) {
                    console.error('错误:', error);
                    chatContainer.removeChild(thinkingContainer);
                    addMessage('抱歉，处理您的请求时出错。', 'assistant');
                    waitingForResponse = false;
                }
            }
            
            // 函数轮询助手响应
            async function pollForResponse(messageId, thinkingContainer) {
                try {
                    const pollInterval = setInterval(async () => {
                        const response = await fetch(`{{ api_base_url }}/{{ assistant.id }}/messages/${messageId}/status`);
                        const data = await response.json();
                        
                        if (data.status === 'completed') {
                            clearInterval(pollInterval);
                            chatContainer.removeChild(thinkingContainer);
                            
                            // 添加助手响应到聊天
                            const content = data.choices[0].message.content;
                            addMessage(content, 'assistant');
                            
                            waitingForResponse = false;
                        } else if (data.status === 'error') {
                            clearInterval(pollInterval);
                            chatContainer.removeChild(thinkingContainer);
                            addMessage('抱歉，生成响应时出错。', 'assistant');
                            waitingForResponse = false;
                        }
                    }, 1000);
                } catch (error) {
                    console.error('轮询响应时出错:', error);
                    chatContainer.removeChild(thinkingContainer);
                    addMessage('抱歉，获取响应时出错。', 'assistant');
                    waitingForResponse = false;
                }
            }
            
            // 事件监听器
            sendButton.addEventListener('click', sendMessage);
            
            userInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            newChatButton.addEventListener('click', function() {
                // 清空聊天
                while (chatContainer.firstChild) {
                    chatContainer.removeChild(chatContainer.firstChild);
                }
                
                // 重置对话
                conversationId = null;
                uploadedImages = [];
                
                // 添加欢迎消息
                addMessage('您好！我是{{ assistant.name }}。我可以如何帮助您今天？', 'assistant');
            });
            
            {% if assistant.has_voice %}
            // 语音输入
            voiceButton.addEventListener('click', function() {
                if ('webkitSpeechRecognition' in window) {
                    const recognition = new webkitSpeechRecognition();
                    recognition.continuous = false;
                    recognition.interimResults = false;
                    
                    voiceButton.disabled = true;
                    voiceButton.textContent = '正在监听...';
                    
                    recognition.start();
                    
                    recognition.onresult = function(event) {
                        const transcript = event.results[0][0].transcript;
                        userInput.value = transcript;
                    };
                    
                    recognition.onend = function() {
                        voiceButton.disabled = false;
                        voiceButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 8a3 3 0 0 0 3-3V3a3 3 0 0 0-6 0v2a3 3 0 0 0 3 3"/><path d="M5 4.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5"/></svg>';
                    };
                    
                    recognition.onerror = function(event) {
                        console.error('语音识别错误:', event.error);
                        voiceButton.disabled = false;
                        voiceButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 8a3 3 0 0 0 3-3V3a3 3 0 0 0-6 0v2a3 3 0 0 0 3 3"/><path d="M5 4.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5"/></svg>';
                    };
                } else {
                    alert('抱歉，您的浏览器不支持语音识别。');
                }
            });
            {% endif %}
            
            {% if assistant.has_multimodal %}
            // 文件上传
            fileUpload.addEventListener('change', async function(e) {
                if (e.target.files.length > 0) {
                    const file = e.target.files[0];
                    
                    // 创建FormData
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                        // 上传图片
                        const response = await fetch('{{ api_base_url }}/{{ assistant.id }}/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        
                        if (data.url) {
                            uploadedImages.push(data.url);
                            
                            // 显示图片预览
                            addMessage(`<img src="${data.url}" alt="上传的图片" style="max-width: 100%; max-height: 300px;">`, 'user');
                        }
                    } catch (error) {
                        console.error('上传图片时出错:', error);
                        alert('上传图片时出错。请重试。');
                    }
                }
            });
            {% endif %}
        });
    </script>
</body>
</html>
"""

# 默认导出模板
DEFAULT_EXPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>与{{ assistant.name }}的对话</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        header {
            border-bottom: 1px solid #eee;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        
        h1 {
            margin: 0;
            color: #3a6ea5;
        }
        
        .meta {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        
        .conversation {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .message {
            max-width: 90%;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        
        .user {
            background-color: #e3f2fd;
            align-self: flex-end;
        }
        
        .assistant {
            background-color: #f5f5f5;
            align-self: flex-start;
        }
        
        .timestamp {
            font-size: 0.8rem;
            color: #999;
            text-align: right;
            margin-top: 0.5rem;
        }
        
        footer {
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <header>
        <h1>与{{ assistant.name }}的对话</h1>
        <div class="meta">
            <div>对话：{{ conversation.title }}</div>
            <div>日期：{{ conversation.created_at }}</div>
        </div>
    </header>
    
    <div class="conversation">
        {% for message in messages %}
        <div class="message {{ message.role }}">
            <div class="content">{{ message.content }}</div>
            <div class="timestamp">{{ message.created_at }}</div>
        </div>
        {% endfor %}
    </div>
    
    <footer>
        <p>导出于{{ export_date }}</p>
    </footer>
</body>
</html>
"""
