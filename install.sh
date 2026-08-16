#!/usr/bin/env bash
# mcode-theme 一键安装脚本（幂等；MUST NOT 使用 sudo）
#
# 用法: ./install.sh [--prefix <目录>]     # 默认 ~/.local
# 退出码: 0 = 成功 | 1 = 失败 | 2 = 参数错误
set -euo pipefail

PREFIX="${HOME}/.local"

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix)
      [ $# -ge 2 ] || { echo "error: --prefix 缺少目录参数" >&2; exit 2; }
      PREFIX="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,6p' "$0"; exit 0 ;;
    *)
      echo "error: 未知参数 $1（用法: ./install.sh [--prefix <目录>]）" >&2
      exit 2 ;;
  esac
done

[ -n "${PREFIX}" ] || { echo "error: --prefix 目录为空" >&2; exit 2; }

# ---- 1. python3 ≥ 3.8 ----
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: 未找到 python3（需要 ≥ 3.8）" >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "error: python3 版本过低（$(python3 -V 2>&1)，需要 ≥ 3.8）" >&2
  exit 1
fi
echo "==> python3 $(python3 -V 2>&1 | awk '{print $2}') 满足要求"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${PREFIX}/bin"

# ---- 2. 复制工具与依赖（幂等：已存在文件先备份 .old） ----
FILES="mcode-theme mcode_theme_lib.py web.py logo_styles.py validate-themes.py"
for f in ${FILES}; do
  if [ ! -f "${SRC_DIR}/${f}" ]; then
    echo "error: 源文件缺失 ${SRC_DIR}/${f}" >&2
    exit 1
  fi
done

mkdir -p "${BIN_DIR}"
for f in ${FILES}; do
  if [ -e "${BIN_DIR}/${f}" ]; then
    cp -f "${BIN_DIR}/${f}" "${BIN_DIR}/${f}.old" 2>/dev/null || true
  fi
  cp -f "${SRC_DIR}/${f}" "${BIN_DIR}/${f}"
  chmod +x "${BIN_DIR}/${f}" 2>/dev/null || true
done
mkdir -p "${BIN_DIR}/web"
if [ -e "${BIN_DIR}/web/index.html" ]; then
  cp -f "${BIN_DIR}/web/index.html" "${BIN_DIR}/web/index.html.old" 2>/dev/null || true
fi
cp -f "${SRC_DIR}/web/index.html" "${BIN_DIR}/web/index.html"
echo "==> 已复制工具与依赖到 ${BIN_DIR}（旧文件保留为 .old）"

# ---- 3. PATH 检查提示 ----
IN_PATH=0
case ":${PATH}:" in
  *":${BIN_DIR}:"*) IN_PATH=1 ;;
esac
if [ "${IN_PATH}" != "1" ]; then
  echo "==> 提示: ${BIN_DIR} 不在 PATH 中，请执行以下任一条："
  echo "    echo 'export PATH=\"${BIN_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
  echo "    或临时使用: export PATH=\"${BIN_DIR}:\$PATH\""
fi

# ---- 4. 摘要 ----
echo ""
echo "==> 安装完成 ✓"
echo "    mcode-theme list                # 查看主题"
echo "    mcode-theme apply <name>        # 应用主题"
echo "    mcode-theme install <url|json>  # 校验并安装主题包"
echo "    mcode-theme update              # 检测 mcode 升级"
echo "    mcode-theme web                 # Web 可视化配置器"
echo "    重启 mcode 后生效"
[ "${IN_PATH}" != "1" ] && echo "    注意: 需先将 ${BIN_DIR} 加入 PATH"
exit 0
