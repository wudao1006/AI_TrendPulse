"""
动态 User-Agent 生成器
根据规律随机生成真实的 User-Agent,避免维护大量静态列表
"""

import random


class UserAgentGenerator:
    """动态生成真实的 User-Agent"""

    # 操作系统模板
    OS_TEMPLATES = {
        'windows': [
            'Windows NT 10.0; Win64; x64',
            'Windows NT 11.0; Win64; x64',
            'Windows NT 6.1; Win64; x64',  # Windows 7
            'Windows NT 6.3; Win64; x64',  # Windows 8.1
        ],
        'macos': [
            'Macintosh; Intel Mac OS X 10_15_7',
            'Macintosh; Intel Mac OS X 13_5_2',
            'Macintosh; Intel Mac OS X 14_0',
            'Macintosh; Intel Mac OS X 14_1',
            'Macintosh; Intel Mac OS X 13_6',
        ],
        'linux': [
            'X11; Linux x86_64',
            'X11; Ubuntu; Linux x86_64',
            'X11; Fedora; Linux x86_64',
        ]
    }

    # Chrome 版本范围 (100-122) - 扩大范围以增加多样性
    CHROME_VERSIONS = list(range(100, 123))

    # Firefox 版本范围 (110-122) - 注意：Playwright使用Chromium，不应使用Firefox UA
    FIREFOX_VERSIONS = list(range(110, 123))

    # Safari 版本
    SAFARI_VERSIONS = ['16.5', '16.6', '17.0', '17.1']

    # WebKit 版本 (基本固定)
    WEBKIT_VERSION = '537.36'

    # Gecko 版本 (基本固定)
    GECKO_VERSION = '20100101'

    @staticmethod
    def _get_random_os(os_type=None):
        """获取随机操作系统信息"""
        if os_type is None:
            os_type = random.choice(['windows', 'macos', 'linux'])
        return random.choice(UserAgentGenerator.OS_TEMPLATES[os_type])

    @staticmethod
    def generate_chrome(os_type=None):
        """
        生成 Chrome User-Agent

        格式: Mozilla/5.0 (OS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/版本 Safari/537.36
        """
        os_info = UserAgentGenerator._get_random_os(os_type)
        chrome_version = random.choice(UserAgentGenerator.CHROME_VERSIONS)

        return (f"Mozilla/5.0 ({os_info}) "
                f"AppleWebKit/{UserAgentGenerator.WEBKIT_VERSION} "
                f"(KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.0.0 "
                f"Safari/{UserAgentGenerator.WEBKIT_VERSION}")

    @staticmethod
    def generate_firefox(os_type=None):
        """
        生成 Firefox User-Agent

        格式: Mozilla/5.0 (OS; rv:版本) Gecko/20100101 Firefox/版本
        """
        # Firefox 的 OS 格式略有不同
        if os_type == 'macos' or (os_type is None and random.random() < 0.3):
            os_templates = [
                'Macintosh; Intel Mac OS X 10.15',
                'Macintosh; Intel Mac OS X 14.0',
                'Macintosh; Intel Mac OS X 13.5',
            ]
            os_info = random.choice(os_templates)
        elif os_type == 'linux' or (os_type is None and random.random() < 0.2):
            os_templates = [
                'X11; Linux x86_64',
                'X11; Ubuntu; Linux x86_64',
            ]
            os_info = random.choice(os_templates)
        else:
            os_info = 'Windows NT 10.0; Win64; x64'

        firefox_version = random.choice(UserAgentGenerator.FIREFOX_VERSIONS)

        return (f"Mozilla/5.0 ({os_info}; rv:{firefox_version}.0) "
                f"Gecko/{UserAgentGenerator.GECKO_VERSION} "
                f"Firefox/{firefox_version}.0")

    @staticmethod
    def generate_edge(os_type='windows'):
        """
        生成 Edge User-Agent

        格式: Mozilla/5.0 (OS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/版本 Safari/537.36 Edg/版本
        """
        os_info = UserAgentGenerator._get_random_os(os_type)
        edge_version = random.choice(UserAgentGenerator.CHROME_VERSIONS)

        return (f"Mozilla/5.0 ({os_info}) "
                f"AppleWebKit/{UserAgentGenerator.WEBKIT_VERSION} "
                f"(KHTML, like Gecko) "
                f"Chrome/{edge_version}.0.0.0 "
                f"Safari/{UserAgentGenerator.WEBKIT_VERSION} "
                f"Edg/{edge_version}.0.0.0")

    @staticmethod
    def generate_safari():
        """
        生成 Safari User-Agent (仅 macOS)

        格式: Mozilla/5.0 (Macintosh; ...) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/版本 Safari/605.1.15
        """
        os_info = UserAgentGenerator._get_random_os('macos')
        safari_version = random.choice(UserAgentGenerator.SAFARI_VERSIONS)

        return (f"Mozilla/5.0 ({os_info}) "
                f"AppleWebKit/605.1.15 "
                f"(KHTML, like Gecko) "
                f"Version/{safari_version} "
                f"Safari/605.1.15")

    @staticmethod
    def generate_random():
        """
        随机生成一个 User-Agent

        重要：由于 Playwright 使用 Chromium 浏览器，只生成 Chrome/Edge User-Agent
        以确保浏览器指纹与 User-Agent 声明一致，避免被检测为机器人

        浏览器分布: Chrome 70%, Edge 30%
        """
        rand = random.random()

        if rand < 0.70:  # 70% Chrome
            return UserAgentGenerator.generate_chrome()
        else:  # 30% Edge
            return UserAgentGenerator.generate_edge()


# 便捷函数
def get_random_user_agent():
    """获取随机生成的 User-Agent"""
    return UserAgentGenerator.generate_random()


def get_chrome_user_agent():
    """获取 Chrome User-Agent"""
    return UserAgentGenerator.generate_chrome()


def get_firefox_user_agent():
    """获取 Firefox User-Agent"""
    return UserAgentGenerator.generate_firefox()


# 测试代码
if __name__ == "__main__":
    print("动态生成的 User-Agent 示例:\n")
    print("=" * 100)

    print("\n【Chrome User-Agents】")
    for i in range(3):
        print(f"{i+1}. {UserAgentGenerator.generate_chrome()}")

    print("\n【Firefox User-Agents】")
    for i in range(3):
        print(f"{i+1}. {UserAgentGenerator.generate_firefox()}")

    print("\n【Edge User-Agents】")
    for i in range(2):
        print(f"{i+1}. {UserAgentGenerator.generate_edge()}")

    print("\n【Safari User-Agents】")
    for i in range(2):
        print(f"{i+1}. {UserAgentGenerator.generate_safari()}")

    print("\n【随机混合 User-Agents (仅 Chrome/Edge，匹配 Playwright Chromium)】")
    for i in range(5):
        print(f"{i+1}. {UserAgentGenerator.generate_random()}")

    print("\n" + "=" * 100)
    print(f"\n✅ 优势:")
    print("  - 无需维护大量静态列表")
    print("  - 每次运行生成全新的 UA,理论上有数百种组合")
    print("  - 符合真实浏览器的 UA 格式规范")
    print("  - 版本号可以轻松更新到最新范围")
    print(f"\n⚠️  重要说明:")
    print("  - 只生成 Chrome/Edge User-Agent，因为 Playwright 使用 Chromium 内核")
    print("  - 这确保浏览器指纹与 User-Agent 完全匹配，避免被检测为机器人")
    print("  - 仍有 23个版本 × 11个OS = 253种 Chrome 组合，足够多样化")