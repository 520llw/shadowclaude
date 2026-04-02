"""
Web UI E2E 测试 (Playwright)

注意：这些测试需要 Playwright 安装和运行的 Web 服务器
"""

import pytest

# 标记为需要 Playwright 的测试
pytestmark = pytest.mark.skipif(
    True,  # 默认跳过，除非有 Playwright 环境
    reason="Playwright tests require browser environment"
)


class TestWebUILoading:
    """测试 Web UI 加载"""
    
    def test_page_loads(self, page):
        """测试页面加载"""
        page.goto("http://localhost:3000")
        assert page.title() == "ShadowClaude"
    
    def test_chat_interface_visible(self, page):
        """测试聊天界面可见"""
        page.goto("http://localhost:3000")
        assert page.is_visible("[data-testid='chat-input']")


class TestWebUIChat:
    """测试 Web UI 聊天"""
    
    def test_send_message(self, page):
        """测试发送消息"""
        page.goto("http://localhost:3000")
        
        page.fill("[data-testid='chat-input']", "Hello")
        page.click("[data-testid='send-button']")
        
        # 等待响应
        page.wait_for_selector("[data-testid='assistant-message']")
    
    def test_streaming_response(self, page):
        """测试流式响应"""
        page.goto("http://localhost:3000")
        
        page.fill("[data-testid='chat-input']", "Test streaming")
        page.click("[data-testid='send-button']")
        
        # 验证流式显示
        page.wait_for_selector(".streaming-indicator")


class TestWebUIFileUpload:
    """测试 Web UI 文件上传"""
    
    def test_upload_file(self, page):
        """测试上传文件"""
        page.goto("http://localhost:3000")
        
        page.set_input_files("[data-testid='file-upload']", "test.txt")
        
        assert page.is_visible("[data-testid='uploaded-file']")


class TestWebUISettings:
    """测试 Web UI 设置"""
    
    def test_open_settings(self, page):
        """测试打开设置"""
        page.goto("http://localhost:3000")
        
        page.click("[data-testid='settings-button']")
        
        assert page.is_visible("[data-testid='settings-modal']")
    
    def test_change_model(self, page):
        """测试更改模型"""
        page.goto("http://localhost:3000")
        page.click("[data-testid='settings-button']")
        
        page.select_option("[data-testid='model-select']", "claude-opus-4")
        page.click("[data-testid='save-settings']")
        
        # 设置应保存
        page.reload()
        page.click("[data-testid='settings-button']")
        selected = page.eval_on_selector(
            "[data-testid='model-select']",
            "el => el.value"
        )
        assert selected == "claude-opus-4"
