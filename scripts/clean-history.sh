#!/usr/bin/env bash
# =====================================================
# git 历史敏感信息清理脚本
#
# 用途：从 git 历史中移除曾意外提交的明文密钥、密码等敏感信息。
# 工具：git-filter-repo（推荐，需 pip install git-filter-repo）
#
# !!! 警告 !!!
# 1. 此操作会重写 git 历史，所有协作者必须重新 clone 仓库。
# 2. 运行前务必创建完整备份。
# 3. 重写历史后需强制推送（force push），请确认团队已知晓。
# 4. 如果仓库已公开，密钥已泄露，请立即轮换所有密钥。
# =====================================================

set -euo pipefail

# ---------- 配置区 ----------

# 需要从历史中清除的敏感字符串（格式：替换前==>替换后）
# 每行一条，左侧为需要清除的真实值，右侧为占位符
REPLACEMENTS=(
    # 注意：长字符串必须在短字符串之前，避免部分匹配导致残留
    "kFIWF6PMiOJYlQBKGUHuNZ2hGHvzq96CjKjYHg4M4YkqiUHENsS_LGZRBWAgp4R0==>REDACTED_SECRET_KEY"
    "WC2Asvn5Pd6MDDqH==>REDACTED_SMTP_PASSWORD"
    "whataicompass@126.com==>REDACTED_SMTP_EMAIL"
    "whataicompass==>REDACTED_SMTP_USER"
    "compass.whatai.me==>REDACTED_DOMAIN"
    "creator123==>REDACTED_MYSQL_PASSWORD"
)

# 需要完全删除的文件路径（.env 等包含密钥的文件）
FILES_TO_REMOVE=(
    # "backend/.env"
    # ".env"
    # "frontend/.env"
)

# 备份目录（默认在仓库同级目录下创建）
BACKUP_DIR="../AnalysisYoutube_backup_$(date +%Y%m%d_%H%M%S)"

# ---------- 前置检查 ----------

echo "=========================================="
echo " git 历史敏感信息清理脚本"
echo "=========================================="
echo ""

# 检查 git 仓库
if [ ! -d ".git" ]; then
    echo "[ERROR] 当前目录不是 git 仓库根目录，请 cd 到仓库根目录后运行。" >&2
    exit 1
fi

# 检查 git-filter-repo 是否安装
if ! command -v git-filter-repo &>/dev/null; then
    echo "[ERROR] git-filter-repo 未安装。" >&2
    echo "        安装方法：pip install git-filter-repo" >&2
    exit 1
fi

# 检查是否有需要清理的内容
if [ ${#REPLACEMENTS[@]} -eq 0 ] && [ ${#FILES_TO_REMOVE[@]} -eq 0 ]; then
    echo "[WARNING] REPLACEMENTS 和 FILES_TO_REMOVE 均为空。" >&2
    echo "          请编辑脚本，填入需要清除的敏感字符串或文件路径。" >&2
    exit 1
fi

# 检查是否有未提交的更改
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    echo "[WARNING] 存在未提交的更改，建议先提交或 stash。" >&2
    read -rp "是否继续？(y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "已取消。"
        exit 0
    fi
fi

# ---------- 确认提示 ----------

echo ""
echo "!!! 危险操作警告 !!!"
echo "此脚本将重写 git 历史，所有协作者必须重新 clone。"
echo "密钥如果已泄露，请立即轮换，仅清理历史无法阻止密钥被滥用。"
echo ""
echo "将执行以下操作："
if [ ${#REPLACEMENTS[@]} -gt 0 ]; then
    echo "  - 替换 ${#REPLACEMENTS[@]} 个敏感字符串"
fi
if [ ${#FILES_TO_REMOVE[@]} -gt 0 ]; then
    echo "  - 删除 ${#FILES_TO_REMOVE[@]} 个文件"
fi
echo "  - 备份到: ${BACKUP_DIR}"
echo ""
read -rp "确认执行？输入 YES 继续: " confirm
if [ "$confirm" != "YES" ]; then
    echo "已取消。"
    exit 0
fi

# ---------- 备份 ----------

echo ""
echo "[1/4] 创建备份..."
cp -a . "${BACKUP_DIR}"
echo "      备份完成: ${BACKUP_DIR}"

# ---------- 构建替换表达式 ----------

echo ""
echo "[2/4] 构建替换规则..."

BLOB_REPLACEMENT_FILE=$(mktemp)
trap 'rm -f "${BLOB_REPLACEMENT_FILE}"' EXIT

for entry in "${REPLACEMENTS[@]}"; do
    old="${entry%%==>*}"
    new="${entry#*==>}"
    if [ -z "$old" ]; then
        echo "[WARNING] 跳过空字符串: ${entry}" >&2
        continue
    fi
    # git-filter-repo blob 替换格式：literal:old==>new
    echo "literal:${old}==>literal:${new}" >> "${BLOB_REPLACEMENT_FILE}"
done

# ---------- 执行替换 ----------

echo ""
echo "[3/4] 执行 git 历史重写..."

# 删除指定文件
for filepath in "${FILES_TO_REMOVE[@]}"; do
    if [ -n "$filepath" ]; then
        echo "      删除文件: ${filepath}"
        git filter-repo --invert-paths --path "${filepath}" --force
    fi
done

# 替换敏感字符串
if [ -s "${BLOB_REPLACEMENT_FILE}" ]; then
    echo "      替换敏感字符串（共 ${#REPLACEMENTS[@]} 条）..."
    git filter-repo --replace-text "${BLOB_REPLACEMENT_FILE}" --force
fi

# ---------- 验证 ----------

echo ""
echo "[4/4] 验证清理结果..."

found_secrets=0

for entry in "${REPLACEMENTS[@]}"; do
    old="${entry%%==>*}"
    if [ -z "$old" ]; then
        continue
    fi
    # 在当前代码和历史中搜索
    if git log --all --full-history -p -S "$old" 2>/dev/null | grep -q "$old"; then
        echo "      [FAIL] 仍发现敏感字符串: ${old:0:8}..." >&2
        found_secrets=$((found_secrets + 1))
    else
        echo "      [OK] 已清除: ${old:0:8}..."
    fi
done

for filepath in "${FILES_TO_REMOVE[@]}"; do
    if [ -n "$filepath" ]; then
        if git log --all --full-history -- "$filepath" 2>/dev/null | grep -q "$filepath"; then
            echo "      [FAIL] 文件仍存在于历史中: ${filepath}" >&2
            found_secrets=$((found_secrets + 1))
        else
            echo "      [OK] 已从历史中删除: ${filepath}"
        fi
    fi
done

# ---------- 结果报告 ----------

echo ""
echo "=========================================="
if [ $found_secrets -eq 0 ]; then
    echo " 清理完成：所有敏感信息已从历史中移除"
else
    echo " 清理完成，但有 ${found_secrets} 项验证失败"
    echo " 请检查替换规则是否正确，或手动审查历史"
fi
echo "=========================================="
echo ""
echo "后续步骤："
echo "  1. 轮换所有曾泄露的密钥（仅清理历史不足以保证安全）"
echo "  2. 通知所有协作者删除旧仓库并重新 clone"
echo "  3. 强制推送到远程仓库：git push origin --force --all"
echo "  4. 确认 .env 文件已在 .gitignore 中"
echo "  5. 删除备份目录：rm -rf ${BACKUP_DIR}"
echo ""

if [ $found_secrets -gt 0 ]; then
    exit 1
fi
