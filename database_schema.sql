-- ============================================
-- Invoice 자동 인식 시스템 - 데이터베이스 스키마
-- Database: invoice_db
-- DBMS: Microsoft SQL Server
-- ============================================

USE invoice_db;
GO

-- ============================================
-- 1. CustomUser (사용자) 테이블
-- ============================================
IF OBJECT_ID('users', 'U') IS NOT NULL
    DROP TABLE users;
GO

CREATE TABLE users (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    password NVARCHAR(128) NOT NULL,
    last_login DATETIME2 NULL,
    is_superuser BIT NOT NULL DEFAULT 0,
    username NVARCHAR(150) NOT NULL UNIQUE,
    first_name NVARCHAR(150) NOT NULL DEFAULT '',
    last_name NVARCHAR(150) NOT NULL DEFAULT '',
    email NVARCHAR(254) NOT NULL DEFAULT '',
    is_staff BIT NOT NULL DEFAULT 0,
    is_active BIT NOT NULL DEFAULT 1,
    date_joined DATETIME2 NOT NULL DEFAULT GETDATE(),

    -- 커스텀 필드
    user_type NVARCHAR(10) NOT NULL DEFAULT 'customs',
    customs_code NVARCHAR(5) NULL UNIQUE,
    customs_name NVARCHAR(100) NULL,
    is_first_login BIT NOT NULL DEFAULT 1,

    CONSTRAINT CK_user_type CHECK (user_type IN ('admin', 'customs'))
);
GO

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_customs_code ON users(customs_code);
CREATE INDEX idx_users_user_type ON users(user_type);
GO

-- ============================================
-- 2. Service (서비스) 테이블
-- ============================================
IF OBJECT_ID('services', 'U') IS NOT NULL
    DROP TABLE services;
GO

CREATE TABLE services (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX idx_services_name ON services(name);
CREATE INDEX idx_services_is_active ON services(is_active);
GO

-- ============================================
-- 3. ServiceUser (서비스-사용자 연결) 테이블
-- ============================================
IF OBJECT_ID('service_users', 'U') IS NOT NULL
    DROP TABLE service_users;
GO

CREATE TABLE service_users (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    service_id BIGINT NOT NULL,
    user_id BIGINT NULL,
    is_default BIT NOT NULL DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_service_users_service FOREIGN KEY (service_id)
        REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_service_users_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT UQ_service_users_service_user UNIQUE (service_id, user_id)
);
GO

CREATE INDEX idx_service_users_service ON service_users(service_id);
CREATE INDEX idx_service_users_user ON service_users(user_id);
CREATE INDEX idx_service_users_is_default ON service_users(is_default);
GO

-- ============================================
-- 4. Declaration (신고서) 테이블
-- ============================================
IF OBJECT_ID('declarations', 'U') IS NOT NULL
    DROP TABLE declarations;
GO

CREATE TABLE declarations (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    service_id BIGINT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    declaration_type NVARCHAR(20) NOT NULL,
    description NVARCHAR(MAX) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_declarations_service FOREIGN KEY (service_id)
        REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT CK_declaration_type CHECK (declaration_type IN ('export', 'import', 'correction'))
);
GO

CREATE INDEX idx_declarations_service ON declarations(service_id);
CREATE INDEX idx_declarations_type ON declarations(declaration_type);
CREATE INDEX idx_declarations_is_active ON declarations(is_active);
GO

-- ============================================
-- 5. MappingInfo (매핑정보) 테이블
-- ============================================
IF OBJECT_ID('mapping_info', 'U') IS NOT NULL
    DROP TABLE mapping_info;
GO

CREATE TABLE mapping_info (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    declaration_id BIGINT NOT NULL,
    service_user_id BIGINT NULL,
    unipass_field_name NVARCHAR(200) NOT NULL,
    db_table_name NVARCHAR(100) NOT NULL,
    db_field_name NVARCHAR(100) NOT NULL,
    priority INT NOT NULL DEFAULT 0,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_mapping_info_declaration FOREIGN KEY (declaration_id)
        REFERENCES declarations(id) ON DELETE CASCADE,
    CONSTRAINT FK_mapping_info_service_user FOREIGN KEY (service_user_id)
        REFERENCES service_users(id) ON DELETE CASCADE
);
GO

CREATE INDEX idx_mapping_info_declaration ON mapping_info(declaration_id);
CREATE INDEX idx_mapping_info_service_user ON mapping_info(service_user_id);
CREATE INDEX idx_mapping_info_priority ON mapping_info(priority);
GO

-- ============================================
-- 6. PromptConfig (프롬프트 설정) 테이블
-- ============================================
IF OBJECT_ID('prompt_configs', 'U') IS NOT NULL
    DROP TABLE prompt_configs;
GO

CREATE TABLE prompt_configs (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    mapping_id BIGINT NOT NULL,
    prompt_type NVARCHAR(20) NOT NULL,
    prompt_text NVARCHAR(MAX) NOT NULL,
    service_user_id BIGINT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    created_by_id BIGINT NULL,

    CONSTRAINT FK_prompt_configs_mapping FOREIGN KEY (mapping_id)
        REFERENCES mapping_info(id) ON DELETE CASCADE,
    CONSTRAINT FK_prompt_configs_service_user FOREIGN KEY (service_user_id)
        REFERENCES service_users(id) ON DELETE CASCADE,
    CONSTRAINT FK_prompt_configs_created_by FOREIGN KEY (created_by_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT CK_prompt_type CHECK (prompt_type IN ('basic', 'additional')),
    CONSTRAINT UQ_prompt_configs_mapping_type_service_user
        UNIQUE (mapping_id, prompt_type, service_user_id)
);
GO

CREATE INDEX idx_prompt_configs_mapping ON prompt_configs(mapping_id);
CREATE INDEX idx_prompt_configs_type ON prompt_configs(prompt_type);
CREATE INDEX idx_prompt_configs_service_user ON prompt_configs(service_user_id);
GO

-- ============================================
-- 7. InvoiceProcessLog (인보이스 처리 로그) 테이블
-- ============================================
IF OBJECT_ID('invoice_process_logs', 'U') IS NOT NULL
    DROP TABLE invoice_process_logs;
GO

CREATE TABLE invoice_process_logs (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    service_user_id BIGINT NOT NULL,
    declaration_id BIGINT NOT NULL,
    image_file NVARCHAR(255) NOT NULL,
    ocr_text NVARCHAR(MAX) NULL,
    gpt_request NVARCHAR(MAX) NULL,
    gpt_response NVARCHAR(MAX) NULL,
    result_json NVARCHAR(MAX) NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message NVARCHAR(MAX) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    completed_at DATETIME2 NULL,
    processing_time FLOAT NULL,

    CONSTRAINT FK_invoice_process_logs_service_user FOREIGN KEY (service_user_id)
        REFERENCES service_users(id) ON DELETE CASCADE,
    CONSTRAINT FK_invoice_process_logs_declaration FOREIGN KEY (declaration_id)
        REFERENCES declarations(id) ON DELETE CASCADE,
    CONSTRAINT CK_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);
GO

CREATE INDEX idx_invoice_process_logs_service_user ON invoice_process_logs(service_user_id);
CREATE INDEX idx_invoice_process_logs_declaration ON invoice_process_logs(declaration_id);
CREATE INDEX idx_invoice_process_logs_status ON invoice_process_logs(status);
CREATE INDEX idx_invoice_process_logs_created_at ON invoice_process_logs(created_at DESC);
GO

-- ============================================
-- Django 관련 테이블 (자동 생성되지만 참고용)
-- ============================================

-- django_migrations
IF OBJECT_ID('django_migrations', 'U') IS NOT NULL
    DROP TABLE django_migrations;
GO

CREATE TABLE django_migrations (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    app NVARCHAR(255) NOT NULL,
    name NVARCHAR(255) NOT NULL,
    applied DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- django_content_type
IF OBJECT_ID('django_content_type', 'U') IS NOT NULL
    DROP TABLE django_content_type;
GO

CREATE TABLE django_content_type (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    app_label NVARCHAR(100) NOT NULL,
    model NVARCHAR(100) NOT NULL,
    CONSTRAINT UQ_django_content_type_app_label_model UNIQUE (app_label, model)
);
GO

-- django_session
IF OBJECT_ID('django_session', 'U') IS NOT NULL
    DROP TABLE django_session;
GO

CREATE TABLE django_session (
    session_key NVARCHAR(40) PRIMARY KEY,
    session_data NVARCHAR(MAX) NOT NULL,
    expire_date DATETIME2 NOT NULL
);
GO

CREATE INDEX idx_django_session_expire_date ON django_session(expire_date);
GO

-- ============================================
-- 초기 데이터 삽입
-- ============================================

-- 관리자 계정 (비밀번호: P@ssw0rd)
-- Django에서 해시된 비밀번호 생성: pbkdf2_sha256$600000$...
INSERT INTO users (password, is_superuser, username, email, is_staff, is_active, date_joined, user_type, is_first_login)
VALUES (
    'pbkdf2_sha256$600000$temp$temppasswordhash', -- 실제 Django에서 생성해야 함
    1,
    'admin',
    'admin@invoice.com',
    1,
    1,
    GETDATE(),
    'admin',
    0
);
GO

-- 샘플 관세사 계정
INSERT INTO users (password, is_superuser, username, is_staff, is_active, date_joined, user_type, customs_code, customs_name, is_first_login)
VALUES
    ('pbkdf2_sha256$600000$temp$temppasswordhash', 0, '6N001', 0, 1, GETDATE(), 'customs', '6N001', 'A관세사', 1),
    ('pbkdf2_sha256$600000$temp$temppasswordhash', 0, '6N002', 0, 1, GETDATE(), 'customs', '6N002', '우리관세사', 1);
GO

-- 샘플 서비스
INSERT INTO services (name, description, is_active, created_at, updated_at)
VALUES
    ('RK통관', 'RK통관 서비스', 1, GETDATE(), GETDATE()),
    ('협회통관', '협회통관 서비스', 1, GETDATE(), GETDATE()),
    ('HelpManager', 'Help Manager 서비스', 1, GETDATE(), GETDATE());
GO

-- 샘플 신고서
DECLARE @service_id BIGINT;
SELECT @service_id = id FROM services WHERE name = 'RK통관';

INSERT INTO declarations (service_id, name, declaration_type, description, is_active, created_at, updated_at)
VALUES
    (@service_id, '수입신고서', 'import', '수입신고서 관리', 1, GETDATE(), GETDATE()),
    (@service_id, '수출신고서', 'export', '수출신고서 관리', 1, GETDATE(), GETDATE()),
    (@service_id, '수출정정', 'correction', '수출정정 관리', 1, GETDATE(), GETDATE());
GO

-- ============================================
-- 스키마 검증 쿼리
-- ============================================

-- 생성된 테이블 확인
SELECT
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.tables t
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
WHERE t.name IN (
    'users', 'services', 'service_users', 'declarations',
    'mapping_info', 'prompt_configs', 'invoice_process_logs'
)
ORDER BY t.name, c.column_id;
GO

-- 외래 키 관계 확인
SELECT
    fk.name AS ForeignKeyName,
    tp.name AS ParentTable,
    cp.name AS ParentColumn,
    tr.name AS ReferencedTable,
    cr.name AS ReferencedColumn
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
ORDER BY tp.name, fk.name;
GO

-- 인덱스 확인
SELECT
    t.name AS TableName,
    i.name AS IndexName,
    i.type_desc AS IndexType,
    c.name AS ColumnName
FROM sys.indexes i
INNER JOIN sys.tables t ON i.object_id = t.object_id
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE t.name IN (
    'users', 'services', 'service_users', 'declarations',
    'mapping_info', 'prompt_configs', 'invoice_process_logs'
)
AND i.is_primary_key = 0
ORDER BY t.name, i.name;
GO

PRINT 'Invoice 시스템 데이터베이스 스키마 생성 완료!';
GO
