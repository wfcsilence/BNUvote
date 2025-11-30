import time
import json
import pandas as pd
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    print("✅ 所有库导入成功！")
except ImportError as e:
    print(f"❌ 库导入失败: {e}")
    print("请运行: pip install selenium webdriver-manager pandas flask")
    exit(1)

# HTML模板（保持不变）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>北师大十佳大学生投票实时统计</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .stats-bar {
            background: #f8f9fa;
            padding: 20px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            border-bottom: 1px solid #e9ecef;
        }
        .stat-item {
            text-align: center;
            padding: 10px 20px;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            font-size: 0.9em;
            color: #6c757d;
            margin-top: 5px;
        }
        .last-update {
            text-align: center;
            padding: 15px;
            background: #e3f2fd;
            color: #1976d2;
            font-weight: bold;
        }
        .candidates-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .candidate-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-left: 5px solid #3498db;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .candidate-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        .candidate-card.top3 {
            border-left-color: #e74c3c;
            background: linear-gradient(135deg, #fff, #ffeaa7);
        }
        .candidate-card.top3 .rank {
            background: #e74c3c;
        }
        .candidate-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .rank {
            background: #3498db;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2em;
        }
        .candidate-info h3 {
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .candidate-number {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .votes {
            text-align: center;
        }
        .vote-count {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .vote-label {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .progress-bar {
            background: #ecf0f1;
            border-radius: 10px;
            height: 8px;
            margin: 15px 0;
            overflow: hidden;
        }
        .progress-fill {
            background: linear-gradient(90deg, #3498db, #2ecc71);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .status-voted {
            background: #2ecc71;
            color: white;
        }
        .status-not-voted {
            background: #e74c3c;
            color: white;
        }
        .refresh-info {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        @media (max-width: 768px) {
            .candidates-grid {
                grid-template-columns: 1fr;
                padding: 15px;
            }
            .stats-bar {
                flex-direction: column;
            }
            .stat-item {
                margin-bottom: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 北师大十佳大学生投票实时统计</h1>
            <div class="subtitle">第二十六届十佳大学生"最具人气奖"投票</div>
        </div>
        
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-value" id="totalCandidates">0</div>
                <div class="stat-label">候选人总数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="totalVotes">0</div>
                <div class="stat-label">总票数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="averageVotes">0</div>
                <div class="stat-label">平均票数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="maxVotes">0</div>
                <div class="stat-label">最高票数</div>
            </div>
        </div>
        
        <div class="last-update">
            🕒 最后更新: <span id="updateTime">正在加载...</span>
            <span id="refreshCountdown" style="margin-left: 20px;"></span>
        </div>
        
        <div class="candidates-grid" id="candidatesGrid">
            <!-- 候选人卡片将通过JavaScript动态生成 -->
            <div style="text-align: center; padding: 40px; color: #7f8c8d;">
                ⏳ 正在加载数据...
            </div>
        </div>
        
        <div class="refresh-info">
            数据每60秒自动更新一次 | 最后刷新: <span id="lastRefreshTime">--:--:--</span>
        </div>
    </div>

    <script>
        let refreshInterval = 60; // 60秒刷新一次
        let countdown = refreshInterval;
        
        function updateCountdown() {
            countdown--;
            document.getElementById('refreshCountdown').textContent = `下次刷新: ${countdown}秒`;
            
            if (countdown <= 0) {
                countdown = refreshInterval;
                fetchData();
            }
        }
        
        function fetchData() {
            fetch('/api/vote-data')
                .then(response => response.json())
                .then(data => {
                    updateDisplay(data);
                    document.getElementById('lastRefreshTime').textContent = new Date().toLocaleTimeString();
                    countdown = refreshInterval;
                })
                .catch(error => {
                    console.error('获取数据失败:', error);
                    document.getElementById('refreshCountdown').textContent = '获取失败，10秒后重试';
                    setTimeout(fetchData, 10000);
                });
        }
        
        function updateDisplay(data) {
            // 更新统计信息
            document.getElementById('totalCandidates').textContent = data.analysis.total_candidates;
            document.getElementById('totalVotes').textContent = data.analysis.total_votes.toLocaleString();
            document.getElementById('averageVotes').textContent = data.analysis.average_votes.toLocaleString();
            document.getElementById('maxVotes').textContent = data.analysis.max_votes.toLocaleString();
            document.getElementById('updateTime').textContent = data.analysis.timestamp;
            
            // 更新候选人列表
            const grid = document.getElementById('candidatesGrid');
            grid.innerHTML = '';
            
            data.candidates.forEach(candidate => {
                const maxVotes = data.analysis.max_votes;
                const percentage = maxVotes > 0 ? (candidate.votes / maxVotes) * 100 : 0;
                
                const card = document.createElement('div');
                card.className = `candidate-card ${candidate.rank <= 3 ? 'top3' : ''}`;
                
                card.innerHTML = `
                    <div class="candidate-header">
                        <div class="rank">${candidate.rank}</div>
                        <div class="candidate-info">
                            <h3>${candidate.name}</h3>
                            <div class="candidate-number">${candidate.number}号候选人</div>
                        </div>
                    </div>
                    
                    <div class="votes">
                        <div class="vote-count">${candidate.votes.toLocaleString()}</div>
                        <div class="vote-label">票数</div>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${percentage}%"></div>
                    </div>
                    
                    <div class="status">
                        <span class="status-badge ${candidate.vote_status.includes('已投') ? 'status-voted' : 'status-not-voted'}">
                            ${candidate.vote_status}
                        </span>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }
        
        // 初始加载
        fetchData();
        
        // 设置定时器
        setInterval(updateCountdown, 1000);
        setInterval(fetchData, refreshInterval * 1000);
        
        // 页面可见性变化时刷新数据
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                fetchData();
            }
        });
    </script>
</body>
</html>
'''

class VoteDataManager:
    def __init__(self):
        self.current_data = None
        self.last_update = None
        self.update_interval = 300  # 5分钟更新一次数据
    
    def get_data(self):
        """获取当前数据，如果数据太旧则更新"""
        if (self.current_data is None or 
            self.last_update is None or 
            (datetime.now() - self.last_update).seconds > self.update_interval):
            self.update_data()
        return self.current_data
    
    def update_data(self):
        """更新数据"""
        print("🔄 正在更新投票数据...")
        try:
            solver = BNUVoteSolver()
            result = solver.run("学号", "密码")
            
            if result:
                self.current_data = result
                self.last_update = datetime.now()
                print(f"✅ 数据更新成功，时间: {self.last_update}")
            else:
                print("❌ 数据更新失败")
        except Exception as e:
            print(f"❌ 更新数据时出错: {e}")

class BNUVoteDataExtractor:
    def __init__(self, driver):
        self.driver = driver
    
    def extract_candidate_data(self):
        """从投票页面提取候选人数据"""
        print("📊 正在提取候选人数据...")
        
        try:
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "info-item"))
            )
            
            # 查找所有候选人项目
            candidate_items = self.driver.find_elements(By.CLASS_NAME, "info-item")
            print(f"✅ 找到 {len(candidate_items)} 个候选人")
            
            candidates_data = []
            
            for item in candidate_items:
                try:
                    candidate_data = self.extract_single_candidate(item)
                    if candidate_data:
                        candidates_data.append(candidate_data)
                except Exception as e:
                    print(f"❌ 提取单个候选人数据失败: {e}")
                    continue
            
            # 按票数排序
            candidates_data.sort(key=lambda x: x['votes'], reverse=True)
            
            return candidates_data
            
        except Exception as e:
            print(f"❌ 提取候选人数据失败: {e}")
            return []
    
    def extract_single_candidate(self, candidate_element):
        """提取单个候选人的数据"""
        try:
            # 提取编号和姓名
            detail_element = candidate_element.find_element(By.CLASS_NAME, "detail")
            name_text = detail_element.find_element(By.TAG_NAME, "p").text
            
            # 解析编号和姓名 (格式: "1号  陈依皓")
            if "号" in name_text:
                number_part = name_text.split("号")[0].strip()
                name_part = name_text.split("号")[1].strip()
                candidate_number = int(number_part)
                candidate_name = name_part
            else:
                candidate_number = 0
                candidate_name = name_text
            
            # 提取票数
            vote_box = candidate_element.find_element(By.CLASS_NAME, "vote-box")
            vote_text = vote_box.find_element(By.CLASS_NAME, "num").text
            
            # 解析票数 (格式: "667票")
            if "票" in vote_text:
                votes = int(vote_text.replace("票", "").strip())
            else:
                votes = int(vote_text)
            
            # 提取投票状态
            try:
                vote_button = candidate_element.find_element(By.CLASS_NAME, "btn-vote")
                vote_status = vote_button.text
            except:
                vote_status = "未知"
            
            # 提取图片URL
            try:
                img_element = candidate_element.find_element(By.TAG_NAME, "img")
                img_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
            except:
                img_url = ""
            
            candidate_data = {
                'number': candidate_number,
                'name': candidate_name,
                'votes': votes,
                'vote_status': vote_status,
                'image_url': img_url,
                'rank': 0  # 稍后排序
            }
            
            print(f"   ✅ 候选人 {candidate_number}号 {candidate_name}: {votes}票")
            return candidate_data
            
        except Exception as e:
            print(f"❌ 解析候选人元素失败: {e}")
            return None
    
    def analyze_vote_results(self, candidates_data):
        """分析投票结果"""
        if not candidates_data:
            return None
        
        total_votes = sum(candidate['votes'] for candidate in candidates_data)
        max_votes = max(candidate['votes'] for candidate in candidates_data)
        min_votes = min(candidate['votes'] for candidate in candidates_data)
        
        # 计算排名
        sorted_candidates = sorted(candidates_data, key=lambda x: x['votes'], reverse=True)
        for i, candidate in enumerate(sorted_candidates, 1):
            candidate['rank'] = i
        
        analysis = {
            'total_candidates': len(candidates_data),
            'total_votes': total_votes,
            'average_votes': round(total_votes / len(candidates_data), 2),
            'max_votes': max_votes,
            'min_votes': min_votes,
            'top_candidates': sorted_candidates[:5],  # 前5名
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return analysis

class BNUVoteSolver:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        print("🚀 正在初始化浏览器...")
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1400,900')
            
            # 避免被检测为自动化工具
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # 设置用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 使用webdriver-manager
            print("📥 正在配置ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ 浏览器初始化成功！")
            
        except Exception as e:
            print(f"❌ 浏览器初始化失败: {e}")
            raise
    
    def solve_login(self, username, password):
        """解决北师大登录问题"""
        print("🎯 正在解决北师大登录问题...")
        
        try:
            # 访问投票页面
            self.driver.get("https://onewechat.bnu.edu.cn/site/vote/index?id=1503")
            time.sleep(5)
            
            print(f"📄 页面标题: {self.driver.title}")
            print(f"🔗 当前URL: {self.driver.current_url}")
            
            # 检查是否需要登录
            if "登录" in self.driver.title:
                print("🔐 需要登录，开始处理...")
                return self.execute_login_sequence(username, password)
            else:
                print("✅ 已登录或无需登录")
                return True
                
        except Exception as e:
            print(f"❌ 访问页面失败: {e}")
            return False
    
    def execute_login_sequence(self, username, password):
        """执行登录序列"""
        try:
            # 等待页面完全加载
            print("⏳ 等待页面完全加载...")
            time.sleep(5)
            
            # 方法1: 使用JavaScript直接设置Vue数据并调用登录方法
            print("🔄 尝试方法1: JavaScript直接登录...")
            if self.javascript_login(username, password):
                return True
            
            # 方法2: 使用Selenium传统方式
            print("🔄 尝试方法2: Selenium传统登录...")
            if self.selenium_login(username, password):
                return True
            
            # 方法3: 使用混合方法
            print("🔄 尝试方法3: 混合登录方法...")
            if self.hybrid_login(username, password):
                return True
            
            print("❌ 所有登录方法都失败了")
            return False
            
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def javascript_login(self, username, password):
        """使用JavaScript直接登录"""
        try:
            # 直接通过JavaScript设置Vue实例的数据并调用登录方法
            script = f"""
            // 设置Vue实例的用户名和密码
            if (typeof vm !== 'undefined') {{
                vm.username = "{username}";
                vm.password = "{password}";
                
                // 检查数据是否设置成功
                console.log('设置后的用户名:', vm.username);
                console.log('设置后的密码:', vm.password);
                
                // 调用登录方法
                vm.login();
                
                return true;
            }} else {{
                console.log('未找到Vue实例vm');
                return false;
            }}
            """
            
            result = self.driver.execute_script(script)
            print("✅ JavaScript登录方法已执行")
            
            # 等待登录完成
            time.sleep(8)
            
            # 检查是否登录成功
            if self.check_login_success():
                return True
            else:
                return False
                
        except Exception as e:
            print(f"JavaScript登录失败: {e}")
            return False
    
    def selenium_login(self, username, password):
        """使用Selenium传统方式登录"""
        try:
            # 查找输入框并填写
            print("🔍 查找输入框...")
            
            # 用户名输入框
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            username_input.clear()
            username_input.send_keys(username)
            print("✅ 已填写用户名")
            
            # 密码输入框
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.clear()
            password_input.send_keys(password)
            print("✅ 已填写密码")
            
            # 查找登录按钮
            login_button = self.driver.find_element(By.CSS_SELECTOR, "div.btn")
            print("✅ 找到登录按钮")
            
            # 多种点击方式尝试
            click_methods = [
                lambda: login_button.click(),  # 普通点击
                lambda: self.driver.execute_script("arguments[0].click();", login_button),  # JS点击
                lambda: self.driver.execute_script("document.querySelector('div.btn').click();")  # 直接JS选择器点击
            ]
            
            for i, method in enumerate(click_methods):
                try:
                    print(f"🖱️ 尝试点击方式 {i+1}...")
                    method()
                    print("✅ 点击成功")
                    break
                except Exception as e:
                    print(f"❌ 点击方式 {i+1} 失败: {e}")
            
            # 等待登录完成
            time.sleep(8)
            
            # 检查是否登录成功
            if self.check_login_success():
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Selenium登录失败: {e}")
            return False
    
    def hybrid_login(self, username, password):
        """混合登录方法"""
        try:
            # 使用JavaScript设置Vue数据，然后用Selenium点击
            script_set_data = f"""
            if (typeof vm !== 'undefined') {{
                vm.username = "{username}";
                vm.password = "{password}";
                console.log('数据设置完成');
                return true;
            }}
            return false;
            """
            
            result = self.driver.execute_script(script_set_data)
            if not result:
                print("❌ 无法设置Vue数据")
                return False
            
            print("✅ Vue数据设置成功")
            time.sleep(2)
            
            # 使用Selenium点击登录按钮
            login_button = self.driver.find_element(By.CSS_SELECTOR, "div.btn")
            
            # 尝试多种点击方式
            for i in range(3):
                try:
                    self.driver.execute_script("arguments[0].click();", login_button)
                    print("✅ 混合登录点击成功")
                    break
                except:
                    if i == 2:
                        print("❌ 混合登录点击失败")
                        return False
            
            # 等待登录完成
            time.sleep(8)
            
            # 检查是否登录成功
            if self.check_login_success():
                return True
            else:
                # 检查是否有错误消息
                self.check_error_message()
                return False
                
        except Exception as e:
            print(f"混合登录失败: {e}")
            return False
    
    def check_login_success(self):
        """检查登录是否成功"""
        current_url = self.driver.current_url
        page_title = self.driver.title
        
        print(f"🔗 登录后URL: {current_url}")
        print(f"📄 登录后标题: {page_title}")
        
        # 判断登录成功的条件
        success_conditions = [
            "login" not in current_url.lower(),
            "登录" not in page_title,
            "vote" in current_url.lower(),
            "投票" in page_title
        ]
        
        if any(success_conditions):
            print("✅ 登录成功！")
            return True
        else:
            print("❌ 登录失败")
            return False
    
    def check_error_message(self):
        """检查错误消息"""
        try:
            # 检查是否有alert弹窗
            alert = self.driver.switch_to.alert
            error_text = alert.text
            print(f"❌ 发现错误弹窗: {error_text}")
            alert.accept()
        except:
            # 没有alert，检查页面中的错误消息
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .warning, .text-danger")
                for elem in error_elements:
                    if elem.is_displayed():
                        print(f"❌ 发现错误消息: {elem.text}")
            except:
                print("⚠️ 未发现明显的错误消息")
    
    def click_vote_statistics_button(self):
        """点击投票统计按钮"""
        print("📊 正在查找投票统计按钮...")
        
        try:
            # 等待页面加载完成
            time.sleep(5)
            
            # 查找"查看投票统计"按钮 - 尝试多种可能的文本
            possible_button_texts = ["查看投票统计", "投票统计", "统计结果", "查看结果", "结果统计"]
            
            for button_text in possible_button_texts:
                try:
                    # 通过XPath查找包含特定文本的按钮
                    statistics_buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{button_text}')]")
                    if statistics_buttons:
                        statistics_button = statistics_buttons[0]
                        print(f"✅ 找到投票统计按钮: '{button_text}'")
                        
                        # 尝试点击
                        try:
                            statistics_button.click()
                            print("✅ 已点击投票统计按钮")
                        except:
                            # 如果普通点击失败，使用JavaScript点击
                            self.driver.execute_script("arguments[0].click();", statistics_button)
                            print("✅ 使用JavaScript点击投票统计按钮")
                        
                        # 等待页面跳转和数据加载
                        print("⏳ 等待投票统计页面加载...")
                        time.sleep(8)
                        
                        # 检查是否成功进入投票统计页面
                        if self.check_vote_statistics_loaded():
                            return True
                        else:
                            print("❌ 可能未成功进入投票统计页面")
                            continue
                except Exception as e:
                    print(f"❌ 查找 '{button_text}' 按钮失败: {e}")
                    continue
            
            # 如果通过文本找不到，尝试通过CSS选择器
            print("🔄 尝试通过CSS选择器查找统计按钮...")
            try:
                # 可能的按钮选择器
                possible_selectors = [
                    ".btn-statistics",
                    ".vote-statistics",
                    ".statistics-btn",
                    "button[class*='statistics']",
                    "button[class*='result']"
                ]
                
                for selector in possible_selectors:
                    try:
                        statistics_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if statistics_buttons:
                            statistics_button = statistics_buttons[0]
                            print(f"✅ 通过选择器找到投票统计按钮: {selector}")
                            
                            self.driver.execute_script("arguments[0].click();", statistics_button)
                            print("✅ 使用JavaScript点击投票统计按钮")
                            
                            time.sleep(8)
                            
                            if self.check_vote_statistics_loaded():
                                return True
                    except:
                        continue
            except Exception as e:
                print(f"❌ 通过CSS选择器查找失败: {e}")
            
            print("❌ 未找到投票统计按钮")
            # 保存当前页面用于调试
            self.save_page_info("no_statistics_button")
            return False
                
        except Exception as e:
            print(f"❌ 点击投票统计按钮失败: {e}")
            return False
    
    def check_vote_statistics_loaded(self):
        """检查投票统计页面是否加载成功"""
        try:
            # 检查是否出现投票数据相关的元素
            checks = [
                lambda: self.driver.find_elements(By.CLASS_NAME, "info-item"),
                lambda: self.driver.find_elements(By.CLASS_NAME, "vote-box"),
                lambda: self.driver.find_elements(By.XPATH, "//*[contains(text(), '候选人')]"),
                lambda: self.driver.find_elements(By.XPATH, "//*[contains(text(), '票')]")
            ]
            
            for check in checks:
                if check():
                    print("✅ 投票统计页面已加载")
                    return True
            
            print("❌ 投票统计页面可能未完全加载")
            return False
            
        except Exception as e:
            print(f"检查投票统计页面失败: {e}")
            return False
    
    def save_page_info(self, filename_prefix):
        """保存页面信息用于调试"""
        try:
            timestamp = time.strftime("%H%M%S")
            filename = f"{filename_prefix}_{timestamp}"
            
            # 保存页面源码
            with open(f"{filename}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"💾 页面源码已保存: {filename}.html")
            
            # 保存截图
            self.driver.save_screenshot(f"{filename}.png")
            print(f"📸 页面截图已保存: {filename}.png")
            
        except Exception as e:
            print(f"保存页面信息失败: {e}")
    
    def extract_vote_data_after_login(self):
        """登录后提取投票数据"""
        print("🎯 开始提取投票数据...")
        
        try:
            # 先点击投票统计按钮
            print("🖱️ 尝试点击投票统计按钮...")
            if not self.click_vote_statistics_button():
                print("⚠️ 无法点击投票统计按钮，尝试直接从当前页面提取数据...")
            
            # 创建数据提取器
            extractor = BNUVoteDataExtractor(self.driver)
            
            # 提取候选人数据
            candidates_data = extractor.extract_candidate_data()
            
            if not candidates_data:
                print("❌ 未能提取到候选人数据")
                return None
            
            # 分析数据
            analysis = extractor.analyze_vote_results(candidates_data)
            
            result = {
                'candidates': candidates_data,
                'analysis': analysis
            }
            
            return result
            
        except Exception as e:
            print(f"❌ 提取投票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self, username, password):
        """运行爬虫"""
        try:
            print("=" * 60)
            print("🗳️  北京师范大学投票数据采集系统")
            print("=" * 60)
            
            # 登录
            if not self.solve_login(username, password):
                print("❌ 登录失败，程序退出")
                return None
            
            print("✅ 登录成功，开始提取投票数据...")
            
            # 提取投票数据（会先尝试点击投票统计按钮）
            result = self.extract_vote_data_after_login()
            
            if result:
                print(f"\n✅ 数据采集成功！")
                print(f"📊 总票数: {result['analysis']['total_votes']}")
                print(f"👥 候选人数量: {len(result['candidates'])}")
                
                # 显示前5名
                print("\n🏆 前5名候选人:")
                for i, candidate in enumerate(result['analysis']['top_candidates'], 1):
                    print(f"   {i}. {candidate['number']}号 {candidate['name']}: {candidate['votes']}票")
            else:
                print("\n❌ 数据提取失败")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 程序运行出错: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if self.driver:
                print("\n🔚 关闭浏览器...")
                self.driver.quit()

# 创建Flask应用
app = Flask(__name__)
data_manager = VoteDataManager()

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/vote-data')
def api_vote_data():
    """API接口，返回投票数据"""
    data = data_manager.get_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '无法获取数据'}), 500

def start_background_updater():
    """启动后台数据更新线程"""
    def update_loop():
        while True:
            data_manager.update_data()
            time.sleep(300)  # 5分钟更新一次
    
    update_thread = threading.Thread(target=update_loop, daemon=True)
    update_thread.start()
    print("🔄 后台数据更新线程已启动")

def main():
    """主函数"""
    print("=" * 60)
    print("🌐 北师大投票数据监控系统")
    print("=" * 60)
    
    # 启动后台数据更新
    start_background_updater()
    
    # 启动Flask服务器
    print("🚀 启动Web服务器...")
    print("📍 访问地址: http://localhost:5000")
    print("⏰ 数据每5分钟自动更新一次")
    print("🔄 网页每60秒自动刷新一次")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()