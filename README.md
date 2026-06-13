# 📄 Resume Forge 2.0 — AI 简历内容生成器

基于 AI 的简历内容生成与优化系统，帮助求职者快速生成针对不同岗位的定制化简历。

## ✨ 功能特性

- 🎯 **岗位分析** — AI 分析职位要求，提取关键技能和匹配点
- 📝 **简历生成** — 根据岗位要求自动生成定制化简历内容
- 🔄 **简历优化** — AI 评审简历质量，提供优化建议
- 📊 **信息统计** — 个人信息管理，支持文件上传和 AI 识别
- 🔑 **多用户支持** — 每个用户独立的 API Key 配置
- 🔒 **数据隔离** — 用户数据完全隔离，保护隐私

## 🆕 2.0 版本更新内容

### 新增功能
- **用户数据隔离** — 每个用户只能看到自己的岗位分析、简历版本、质量评审数据
- **独立 API Key 管理** — 每个用户配置自己的 AI 模型 API Key，不再共享全局配置
- **手动识别模式** — 信息统计页面上传文件后，需手动点击"识别内容"按钮触发 AI 分析
- **API Key 检查** — 未配置 API Key 的用户会收到弹窗提示，引导前往设置页面添加

### 优化改进
- **岗位匹配评分优化** — 修复了匹配度评分为 0 的问题，现在会根据经验相关性给出合理分数
- **简历历史筛选** — 简历页面支持按岗位筛选历史版本
- **前端模型状态显示** — 顶部导航栏实时显示当前模型配置状态（绿色已配置/红色未配置）

### 技术架构
- **后端** — FastAPI + SQLAlchemy + PostgreSQL + pgvector
- **前端** — Vue 3 + Naive UI + Pinia + TypeScript
- **AI 模型** — 支持 DeepSeek、OpenAI、Claude 等兼容接口

## 🚀 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/hello-fengsir/resume-forge.git
cd resume-forge
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置以下必要参数：
# - DB_PASSWORD: 数据库密码
# - ENCRYPTION_KEY: 数据加密密钥（用于加密存储 API Key）
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问系统**
- 前端: http://localhost:8093
- 后端 API: http://localhost:8017

5. **登录并配置**
- 使用默认账号登录（admin / admin123）
- 进入设置页面，添加你的 API Key（DeepSeek/OpenAI/Claude）
- 开始使用 AI 功能

> ⚠️ 首次登录后请立即修改默认密码！

## 📁 项目结构

```
resume-forge/
├── backend/              # 后端服务 (Python FastAPI)
│   ├── app/
│   │   ├── routers/      # API 路由
│   │   ├── services/     # AI 服务引擎
│   │   ├── models/       # 数据库模型
│   │   └── auth/         # 认证模块
│   └── requirements.txt
├── frontend/             # 前端服务 (Vue 3 + Naive UI)
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── stores/       # Pinia 状态管理
│   │   └── api/          # API 接口
│   └── Dockerfile
├── data/                 # 数据库初始化脚本
├── docker-compose.yml    # Docker Compose 配置
└── .env                  # 环境变量配置
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|--------|
| `DB_PASSWORD` | 数据库密码 | your_password_here |
| `ENCRYPTION_KEY` | API Key 加密密钥 | 随机生成的 32 位字符串 |

### AI 模型配置

系统支持以下 AI 模型提供商：
- **DeepSeek** — 推荐，性价比高
- **OpenAI** — GPT-4o、GPT-4 等
- **Claude** — Anthropic Claude 系列

> 💡 每个用户需要在"设置"页面配置自己的 API Key 才能使用 AI 功能。

### 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 8093 | 前端页面 |
| Backend | 8017 | API 服务 |
| Database | 5434 | PostgreSQL |

## 📖 API 文档

启动后访问: http://localhost:8017/docs

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Naive UI](https://www.naiveui.com/)
- [DeepSeek](https://www.deepseek.com/)

## ☕ 赞赏支持

如果这个项目对你有帮助，可以请作者喝杯咖啡：

![赞赏码](images/赞赏码.jpg)

## 📧 联系方式

如有问题，请提交 Issue 或联系作者。

---

**感谢使用 Resume Forge！** 🎉
