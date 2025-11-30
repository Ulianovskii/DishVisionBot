-- 001_add_paid_photos_balance.sql
-- Добавляет баланс платных анализов пользователю

ALTER TABLE users
ADD COLUMN IF NOT EXISTS paid_photos_balance INTEGER NOT NULL DEFAULT 0;
