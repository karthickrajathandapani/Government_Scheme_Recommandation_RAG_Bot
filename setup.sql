-- =====================================================
-- TN Government Scheme RAG Assistant
-- MySQL / XAMPP Setup Script
-- Run in phpMyAdmin SQL tab  OR:
--   mysql -u root < setup.sql
-- =====================================================

CREATE DATABASE IF NOT EXISTS chatbot
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE chatbot;

-- ── users ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    first_name    VARCHAR(100)  NOT NULL,
    last_name     VARCHAR(100)  NOT NULL,
    student_id    VARCHAR(50)   NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME      NULL,
    is_active     TINYINT(1)    DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── student_profiles ──────────────────────────────
CREATE TABLE IF NOT EXISTS student_profiles (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    gender        VARCHAR(20)   NOT NULL,
    community     VARCHAR(50)   NOT NULL,
    current_std   VARCHAR(20)   NOT NULL,
    study_goal    VARCHAR(50)   NOT NULL,
    income_range  VARCHAR(80)   NOT NULL,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── chat_sessions ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    profile_id    INT           NULL,
    session_title VARCHAR(200)  DEFAULT 'New Session',
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── chat_messages ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    session_id    INT           NOT NULL,
    role          ENUM('user','bot') NOT NULL,
    content       TEXT          NOT NULL,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── government_schemes ────────────────────────────
CREATE TABLE IF NOT EXISTS government_schemes (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    scheme_name        VARCHAR(200) NOT NULL,
    category           VARCHAR(100) NOT NULL,
    gender             VARCHAR(30)  NOT NULL,
    community          VARCHAR(100) NOT NULL,
    income_limit       VARCHAR(200) NOT NULL,
    education_level    VARCHAR(150) NOT NULL,
    benefits           TEXT         NOT NULL,
    documents_required TEXT         NOT NULL,
    application_portal VARCHAR(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Seed schemes ──────────────────────────────────
INSERT IGNORE INTO government_schemes
  (scheme_name,category,gender,community,income_limit,education_level,benefits,documents_required,application_portal)
VALUES
('Pudhumai Penn Scheme','Higher Education Support','Female','All communities',
 'No major income restriction','UG / Diploma / ITI',
 'Rs.1,000 per month until course completion',
 'Aadhaar Card,School Transfer Certificate,College Admission Proof,Bank Account Details',
 'Directorate of Collegiate Education'),

('Tamil Pudhalvan Scheme','Higher Education Support','Male','All communities',
 'Applicable mainly for govt school students','UG / Diploma / ITI',
 'Rs.1,000 per month',
 'Aadhaar Card,Community Certificate,Admission Proof,Bank Details',
 'Tamil Nadu Education Portal'),

('First Graduate Scholarship Scheme','Tuition Fee Concession','All genders','All communities',
 'Based on first-generation graduate status','Professional / Engineering / UG',
 'Tuition fee waiver up to eligible limit',
 'First Graduate Certificate,Income Certificate,Community Certificate,Admission Letter',
 'Tamil Nadu Higher Education Department'),

('BC/MBC/DNC Post-Matric Scholarship','Scholarship','All genders','BC / MBC / DNC',
 'Up to Rs.2.5 lakh per annum','UG / PG / Diploma',
 'Tuition fee, hostel fee, maintenance allowance',
 'Community Certificate,Income Certificate,Aadhaar,Bonafide Certificate',
 'BCMBC Welfare Department Portal'),

('SC/ST Post-Matric Scholarship','Scholarship','All genders','SC / ST',
 'Up to Rs.2.5 lakh per annum','UG / PG / Professional Courses',
 'Full fee reimbursement, hostel, maintenance allowance',
 'Caste Certificate,Income Certificate,Aadhaar,Admission Proof',
 'Adi Dravidar Welfare Portal / NSP'),

('EVR Nagammai Scholarship','Women Education Support','Female','All communities',
 'Income-based preference','PG Arts / Science',
 'Financial aid for postgraduate education',
 'Income Certificate,Degree Certificate,Admission Proof,Aadhaar',
 'Directorate of Collegiate Education'),

('Differently Abled Students Scholarship','Disability Welfare','All genders','All communities',
 'Varies','UG / PG / Professional',
 'Tuition, hostel, reader allowance, assistive devices',
 'Disability Certificate,Aadhaar,Income Certificate,Educational Records',
 'Welfare of Differently Abled Department'),

('Central Sector Scholarship Scheme','Merit Scholarship','All genders','All communities',
 'Family income below Rs.4.5 lakh/year','UG / PG',
 'Rs.10,000 to Rs.20,000 per year',
 'Marksheet,Income Certificate,Aadhaar,Bank Details',
 'National Scholarship Portal'),

('Minority Scholarship Scheme','Scholarship','All genders','Minority (Muslim/Christian/Sikh)',
 'Up to prescribed income limits','UG / PG / Technical',
 'Tuition fee and maintenance allowance',
 'Minority Certificate,Income Proof,Academic Records',
 'NSP / Minority Welfare Portal'),

('Pragati Scholarship (AICTE)','Technical Education Support','Female','All communities',
 'Family income below Rs.8 lakh/year','Technical / Professional Courses',
 'Rs.50,000 per year',
 'Income Certificate,Aadhaar,Admission Proof,AICTE Registration',
 'AICTE Scholarship Portal');

-- ── Indexes ───────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_sid      ON users(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_uid   ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_sid   ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_profiles_uid   ON student_profiles(user_id);

SELECT 'Database chatbot setup complete!' AS Status;
