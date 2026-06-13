# 📄 Resume Forge — AI 简历内容生成器

基于 AI 的简历内容生成与优化系统，帮助求职者快速生成针对不同岗位的定制化简历。

## ✨ 功能特性

- 🎯 **岗位分析** — AI 分析职位要求，提取关键技能和匹配点
- 📝 **简历生成** — 根据岗位要求自动生成定制化简历内容
- 🔄 **简历优化** — AI 评审简历质量，提供优化建议
- 📊 **信息统计** — 个人信息管理，支持文件上传和 AI 识别
- 🔑 **多用户支持** — 每个用户独立的 API Key 配置
- 🔒 **数据隔离** — 用户数据完全隔离，保护隐私

## 🚀 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/resume-forge.git
cd resume-forge
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 DeepSeek API Key
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问系统**
- 前端: http://localhost:8093
- 后端 API: http://localhost:8017

### 默认账号

- 用户名: `admin`
- 密码: `admin123`

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

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_PASSWORD` | 数据库密码 | resume-forge-2026 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | https://api.deepseek.com |
| `GENERATE_MODEL` | 生成模型 | deepseek-v4-pro |
| `REVIEW_MODEL` | 评审模型 | deepseek-v4-pro |
| `ENCRYPTION_KEY` | 数据加密密钥 | 需要手动设置 |

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

## 📧 联系方式

如有问题，请提交 Issue
