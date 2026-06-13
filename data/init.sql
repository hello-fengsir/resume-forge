-- Resume Forge 数据库初始化脚本
-- 默认账号: admin / admin123

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys 表
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    encrypted_key VARCHAR(500) NOT NULL,
    model VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 岗位分析表
CREATE TABLE IF NOT EXISTS job_analyses (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    job_title VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    requirements TEXT,
    analysis_result TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 简历版本表
CREATE TABLE IF NOT EXISTS resume_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    job_id VARCHAR(36) REFERENCES job_analyses(id),
    title VARCHAR(200),
    content TEXT,
    match_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 质量评审表
CREATE TABLE IF NOT EXISTS quality_reviews (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    resume_id VARCHAR(36) REFERENCES resume_versions(id),
    score FLOAT,
    review_result TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 信息条目表
CREATE TABLE IF NOT EXISTS info_entries (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    category VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    company VARCHAR(200),
    content TEXT,
    raw_input TEXT,
    source_file VARCHAR(500),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 配置表
CREATE TABLE IF NOT EXISTS app_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 插入默认管理员账号 (密码: admin123, bcrypt hash)
INSERT INTO users (id, username, hashed_password, is_active) VALUES 
('00000000-0000-0000-0000-000000000001', 'admin', '$2b$12$LJ3m4ys3Lk0TSwHjnF4oR.K3VJxqfVYqxSy3TqFG3YfP0z2bSMHGu', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 插入默认配置
INSERT INTO app_config (key, value) VALUES 
('generate_model', 'deepseek-v4-pro'),
('review_model', 'deepseek-v4-pro')
ON CONFLICT (key) DO NOTHING;
