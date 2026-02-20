#!/usr/bin/env bash
# =============================================================================
# start_demo.sh — 启动 adk-demo 的 Merchant Server 和 Client Agent Web UI
#
# 用法（从仓库根目录运行）:
#   bash python/examples/adk-demo/start_demo.sh
#
# 或者直接在 adk-demo 目录运行:
#   bash start_demo.sh
#
# 环境变量（可在 .env 文件中设置，或在运行前 export）:
#   GOOGLE_API_KEY       — 必填，Google Gemini API Key
#   TRON_PRIVATE_KEY     — 必填，Tron 钱包私钥（64位十六进制）
#   FACILITATOR_URL      — 必填，Facilitator 服务地址（默认 http://0.0.0.0:8001）
#   SERVER_HOST          — 可选，Merchant Server 监听地址（默认 0.0.0.0）
#   SERVER_PORT          — 可选，Merchant Server 端口（默认 8000）
#   CLIENT_PORT          — 可选，ADK Web UI 端口（默认 8080）
#   TRON_NETWORK         — 可选，Tron 网络（默认 tron:nile）
# =============================================================================

set -euo pipefail

# --------------------------------------------------------------------------
# 定位脚本所在目录（兼容从任意位置调用）
# --------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$SCRIPT_DIR"

# --------------------------------------------------------------------------
# 颜色输出
# --------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

# --------------------------------------------------------------------------
# 读取配置（支持 .env 文件）
# --------------------------------------------------------------------------
ENV_FILE="$DEMO_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    log_info "加载环境变量: $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

SERVER_HOST="${SERVER_HOST:-0.0.0.0}"
SERVER_PORT="${SERVER_PORT:-8000}"
CLIENT_PORT="${CLIENT_PORT:-8080}"
TRON_NETWORK="${TRON_NETWORK:-tron:nile}"
FACILITATOR_URL="${FACILITATOR_URL:-http://0.0.0.0:8001}"

export TRON_NETWORK FACILITATOR_URL SERVER_HOST SERVER_PORT

# --------------------------------------------------------------------------
# 检查必要环境变量
# --------------------------------------------------------------------------
log_section "环境检查"

if [[ -z "${GOOGLE_API_KEY:-}" && "${GOOGLE_GENAI_USE_VERTEXAI:-}" != "TRUE" ]]; then
    log_error "未设置 GOOGLE_API_KEY 环境变量。"
    log_error "请在 $ENV_FILE 中添加，或运行: export GOOGLE_API_KEY=your_key_here"
    exit 1
fi
log_ok "GOOGLE_API_KEY 已设置"

if [[ -z "${TRON_PRIVATE_KEY:-}" ]]; then
    log_error "未设置 TRON_PRIVATE_KEY 环境变量（钱包签名所必需）。"
    log_error "请在 $ENV_FILE 中添加 Tron 私钥（64位十六进制，测试网专用）。"
    log_error "参考: $DEMO_DIR/.env.example"
    exit 1
fi
export TRON_PRIVATE_KEY
log_ok "TRON_PRIVATE_KEY 已设置（网络: ${TRON_NETWORK}）"

if [[ -z "${PAY_TO_ADDRESS:-}" ]]; then
    log_error "未设置 PAY_TO_ADDRESS 环境变量（Merchant 收款地址）。"
    log_error "请在 $ENV_FILE 中添加 Merchant 的 Tron 钱包地址。"
    log_error "参考: $DEMO_DIR/.env.example"
    exit 1
fi
export PAY_TO_ADDRESS
log_ok "PAY_TO_ADDRESS: ${PAY_TO_ADDRESS}"

log_ok "Facilitator URL: ${FACILITATOR_URL}"

# 检查 uv 是否安装
if ! command -v uv &>/dev/null; then
    log_error "未找到 'uv' 命令。请先安装: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
log_ok "uv $(uv --version) 已安装"

# --------------------------------------------------------------------------
# 安装/同步依赖
# --------------------------------------------------------------------------
log_section "同步依赖"
log_info "Running uv sync (directory: $DEMO_DIR)..."
uv sync --directory="$DEMO_DIR"
log_ok "Dependency sync complete"

# --------------------------------------------------------------------------
# 日志文件
# --------------------------------------------------------------------------
LOG_DIR="$DEMO_DIR/logs"
mkdir -p "$LOG_DIR"
SERVER_LOG="$LOG_DIR/server.log"
CLIENT_LOG="$LOG_DIR/client.log"

# --------------------------------------------------------------------------
# 清理函数：Ctrl+C 时优雅退出
# --------------------------------------------------------------------------
SERVER_PID=""
CLIENT_PID=""

cleanup() {
    echo ""
    log_section "正在关闭所有进程..."
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        log_info "停止 Merchant Server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    if [[ -n "$CLIENT_PID" ]] && kill -0 "$CLIENT_PID" 2>/dev/null; then
        log_info "停止 Client Agent Web UI (PID: $CLIENT_PID)..."
        kill "$CLIENT_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    log_ok "所有进程已退出。"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --------------------------------------------------------------------------
# 启动 Merchant Server
# --------------------------------------------------------------------------
log_section "启动 Merchant Server"
log_info "地址: http://${SERVER_HOST}:${SERVER_PORT}"
log_info "Facilitator: ${FACILITATOR_URL}"
log_info "日志: $SERVER_LOG"

uv --directory="$DEMO_DIR" run server \
    --host "$SERVER_HOST" \
    --port "$SERVER_PORT" \
    > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
log_ok "Merchant Server 已启动 (PID: $SERVER_PID)"

# 等待 Server 就绪（最多 20 秒）
log_info "等待 Merchant Server 就绪..."
WAIT_SECS=0
until curl -sf "http://localhost:${SERVER_PORT}/agents/merchant_agent/.well-known/agent-card.json" > /dev/null 2>&1; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        log_error "Merchant Server 进程意外退出！请查看日志: $SERVER_LOG"
        cat "$SERVER_LOG"
        exit 1
    fi
    if [[ $WAIT_SECS -ge 20 ]]; then
        log_warn "Server 在 20 秒内未响应，继续启动 Client（Server 可能仍在初始化中）..."
        break
    fi
    sleep 1
    WAIT_SECS=$((WAIT_SECS + 1))
done
if [[ $WAIT_SECS -lt 20 ]]; then
    log_ok "Merchant Server 已就绪 ✓"
fi

# --------------------------------------------------------------------------
# 启动 Client Agent Web UI (ADK Web)
# --------------------------------------------------------------------------
log_section "启动 Client Agent Web UI"
log_info "地址: http://localhost:${CLIENT_PORT}"
log_info "日志: $CLIENT_LOG"

uv --directory="$DEMO_DIR" run adk web \
    --port "$CLIENT_PORT" \
    > "$CLIENT_LOG" 2>&1 &
CLIENT_PID=$!
log_ok "Client Agent Web UI 已启动 (PID: $CLIENT_PID)"

# --------------------------------------------------------------------------
# 打印使用说明
# --------------------------------------------------------------------------
log_section "Demo 已启动 🚀"
echo ""
echo -e "  ${BOLD}Merchant Server:${NC}  http://${SERVER_HOST}:${SERVER_PORT}"
echo -e "  ${BOLD}Client Web UI:${NC}    http://localhost:${CLIENT_PORT}"
echo -e "  ${BOLD}Facilitator:${NC}      ${FACILITATOR_URL}"
echo ""
echo -e "  ${BOLD}测试步骤:${NC}"
echo -e "  1. 打开浏览器访问 ${CYAN}http://localhost:${CLIENT_PORT}${NC}"
echo -e "  2. 选择 ${BOLD}client_agent${NC}"
echo -e "  3. 发送消息: ${YELLOW}\"I want to buy a banana\"${NC}"
echo -e "  4. 按照提示确认支付"
echo ""
echo -e "  ${BOLD}钱包配置:${NC}"
echo -e "  - 网络: ${TRON_NETWORK}"
echo ""
echo -e "  ${BOLD}日志文件:${NC}"
echo -e "  - Server: ${SERVER_LOG}"
echo -e "  - Client: ${CLIENT_LOG}"
echo ""
echo -e "  按 ${BOLD}Ctrl+C${NC} 停止所有服务"
echo ""

# --------------------------------------------------------------------------
# 等待子进程（保持脚本运行）
# --------------------------------------------------------------------------
wait "$SERVER_PID" "$CLIENT_PID" 2>/dev/null || true
cleanup
