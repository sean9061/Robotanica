"""
Kinetic-Botanics リアルタイムダッシュボード
映像: 各トラッカーがJPEG圧縮してUDP送信 → ダッシュボードが受信して表示
データ:
  5100: hand JSON  / 5102: hand JPEG frame
  5101: tulip JSON / 5103: tulip JPEG frame

起動:
    python dashboard/dashboard.py
"""

import argparse
import json
import socket
import threading
import time
from collections import deque

import cv2
import numpy as np

# ─────────────────────────────────────────────
#  定数
# ─────────────────────────────────────────────
HAND_UDP_PORT  = 5100
TULIP_UDP_PORT = 5101
PANEL_W, PANEL_H = 640, 360
FRAME_MARGIN = 28          # カメラ映像の余白(px)
ARROW_COL_W  = 60          # 矢印専用カラム幅(px)
WIN_W  = PANEL_W * 2 + ARROW_COL_W  # 1340
WIN_H  = PANEL_H * 2                # 720
TIMEOUT_SEC = 0.5
SERVO_HISTORY_LEN = 50 


# ─────────────────────────────────────────────
#  SharedState
# ─────────────────────────────────────────────
class SharedState:
    def __init__(self):
        self._lock = threading.Lock()

        self.hand_frame  = None   # 受信済みJPEGをデコードしたBGR画像
        self.tulip_frame = None

        # hand tracker データ
        self.servo         = [128, 128, 128]
        self.polar_r       = 0.0
        self.polar_theta   = 0.0
        self.hand_detected = False
        self.last_hand_t   = 0.0
        self.last_hand_frame_t = 0.0
        self.servo_history = deque(maxlen=SERVO_HISTORY_LEN)

        # tulip tracker データ
        self.tulip_x        = 0.5
        self.tulip_y        = 0.5
        self.tulip_w        = 0
        self.tulip_h        = 0
        self.tulip_conf     = 0.0
        self.tulip_detected = False
        self.last_tulip_t   = 0.0
        self.last_tulip_frame_t = 0.0
        self.tulip_pos_history  = deque(maxlen=120)  # (timestamp, x, y, depth)

    def update_hand(self, d: dict):
        with self._lock:
            self.last_hand_t   = time.time()
            self.hand_detected = d.get("detected", False)
            if self.hand_detected:
                self.servo       = d.get("servo", self.servo)
                self.polar_r     = d.get("r", self.polar_r)
                self.polar_theta = d.get("theta_deg", self.polar_theta)
                self.servo_history.append(list(self.servo))

    def update_tulip(self, d: dict):
        with self._lock:
            self.last_tulip_t   = time.time()
            self.tulip_detected = d.get("detected", False)
            if self.tulip_detected:
                self.tulip_x    = d.get("x", self.tulip_x)
                self.tulip_y    = d.get("y", self.tulip_y)
                self.tulip_w    = d.get("w", self.tulip_w)
                self.tulip_h    = d.get("h", self.tulip_h)
                self.tulip_conf = d.get("conf", self.tulip_conf)
                depth_val = (20 * 4) / self.tulip_w if self.tulip_w > 0 else 0.0
                self.tulip_pos_history.append(
                    (self.last_tulip_t, self.tulip_x, self.tulip_y, depth_val)
                )

    def set_hand_frame(self, frame: np.ndarray):
        with self._lock:
            self.hand_frame = frame
            self.last_hand_frame_t = time.time()

    def set_tulip_frame(self, frame: np.ndarray):
        with self._lock:
            self.tulip_frame = frame
            self.last_tulip_frame_t = time.time()

    def snapshot(self):
        with self._lock:
            return {
                "hand_frame":        self.hand_frame.copy()  if self.hand_frame  is not None else None,
                "tulip_frame":       self.tulip_frame.copy() if self.tulip_frame is not None else None,
                "servo":             list(self.servo),
                "polar_r":           self.polar_r,
                "polar_theta":       self.polar_theta,
                "hand_detected":     self.hand_detected,
                "last_hand_t":       self.last_hand_t,
                "last_hand_frame_t": self.last_hand_frame_t,
                "servo_history":     list(self.servo_history),
                "tulip_x":           self.tulip_x,
                "tulip_y":           self.tulip_y,
                "tulip_w":           self.tulip_w,
                "tulip_h":           self.tulip_h,
                "tulip_conf":        self.tulip_conf,
                "tulip_detected":    self.tulip_detected,
                "last_tulip_t":      self.last_tulip_t,
                "last_tulip_frame_t":  self.last_tulip_frame_t,
                "tulip_pos_history":   list(self.tulip_pos_history),
            }


# ─────────────────────────────────────────────
#  ヘルパー
# ─────────────────────────────────────────────
def _make_placeholder(text: str, w: int, h: int) -> np.ndarray:
    img = np.full((h, w, 3), 210, dtype=np.uint8)
    tw, th = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
    cv2.putText(img, text, ((w - tw) // 2, (h + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1, cv2.LINE_AA)
    return img


def _make_arrow_col(h: int, connected: bool = False, t: float = 0.0) -> np.ndarray:
    """>>> スタイルの矢印カラム。connected=True のとき順番に光るアニメーション"""
    col = np.full((h, ARROW_COL_W, 3), 240, dtype=np.uint8)
    ay = h // 2

    # 3つのシェブロン(>) の起点X座標
    n = 3
    chevron_xs = [8, 22, 36]
    cw, ch = 12, 9   # 幅, 半高さ

    if not connected:
        for cx_ch in chevron_xs:
            top = (cx_ch,      ay - ch)
            mid = (cx_ch + cw, ay)
            bot = (cx_ch,      ay + ch)
            cv2.line(col, top, mid, (185, 185, 185), 3, cv2.LINE_AA)
            cv2.line(col, mid, bot, (185, 185, 185), 3, cv2.LINE_AA)
        return col

    # アニメーション: 0.45秒で1周、1つずつ明るく点灯
    period = 0.45
    active = int((t % period) / period * n)

    for i, cx_ch in enumerate(chevron_xs):
        alpha = 1.0 if i == active else 0.2
        color = (
            int(30  + 225 * alpha),
            int(90  + 165 * alpha),
            int(150 + 105 * alpha),
        )
        thickness = 4 if i == active else 2
        top = (cx_ch,      ay - ch)
        mid = (cx_ch + cw, ay)
        bot = (cx_ch,      ay + ch)
        cv2.line(col, top, mid, color, thickness, cv2.LINE_AA)
        cv2.line(col, mid, bot, color, thickness, cv2.LINE_AA)

    return col


def _pad_frame(frame: np.ndarray) -> np.ndarray:
    """PANEL_W×PANEL_H のキャンバスに FRAME_MARGIN の余白を付けて映像を配置"""
    inner_w = PANEL_W - FRAME_MARGIN * 2
    inner_h = PANEL_H - FRAME_MARGIN * 2
    canvas = np.full((PANEL_H, PANEL_W, 3), 240, dtype=np.uint8)
    canvas[FRAME_MARGIN:FRAME_MARGIN + inner_h,
           FRAME_MARGIN:FRAME_MARGIN + inner_w] = cv2.resize(frame, (inner_w, inner_h))
    return canvas


# ─────────────────────────────────────────────
#  スレッド: JSON データ受信
# ─────────────────────────────────────────────
def udp_listen_thread(port: int, which: str, shared: SharedState, stop: threading.Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.2)

    while not stop.is_set():
        try:
            data, _ = sock.recvfrom(4096)
            d = json.loads(data.decode())
            if which == "hand":
                shared.update_hand(d)
            else:
                shared.update_tulip(d)
        except socket.timeout:
            continue
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

    sock.close()


# ─────────────────────────────────────────────
#  スレッド: MJPEG ストリームからフレーム受信
# ─────────────────────────────────────────────
def mjpeg_capture_thread(url: str, which: str, shared: SharedState, stop: threading.Event):
    while not stop.is_set():
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            time.sleep(1.0)
            continue
        while not stop.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            if which == "hand":
                shared.set_hand_frame(frame)
            else:
                shared.set_tulip_frame(frame)
        cap.release()


# ─────────────────────────────────────────────
#  描画ヘルパー
# ─────────────────────────────────────────────
def draw_bar(canvas: np.ndarray, x: int, y: int, w: int, h: int,
             val: float, max_val: float, color=(80, 200, 80)):
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (205, 205, 205), -1)
    fill = int(w * min(val / max(max_val, 1), 1.0))
    cv2.rectangle(canvas, (x, y), (x + fill, y + h), color, -1)
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (160, 160, 160), 1)


def _dot(canvas: np.ndarray, x: int, y: int, connected: bool):
    color = (30, 160, 30) if connected else (40, 40, 200)
    cv2.circle(canvas, (x, y), 6, color, -1, cv2.LINE_AA)


# ─────────────────────────────────────────────
#  下段左: サーボバー
# ─────────────────────────────────────────────
def _render_servo_topview(snap: dict, w: int, h: int) -> np.ndarray:
    """サーボの上面図 (中心から3方向アーム)"""
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)

    cv2.putText(canvas, "SERVO (top view)", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)

    cx = w // 2
    cy = 30 + (h - 50) // 2
    max_r = min((h - 50) // 2 - 15, w // 2 - 55)

    labels = ["S0", "S1", "S2"]
    colors = [(40, 180, 40), (200, 100, 30), (0, 150, 220)]
    base_angles = [0, 120, 240]   # servo_control の thirds と同じ角度

    cv2.circle(canvas, (cx, cy), max_r, (190, 190, 190), 1, cv2.LINE_AA)
    cv2.circle(canvas, (cx, cy), 7, (100, 100, 100), -1, cv2.LINE_AA)

    for i, (angle_deg, color, lbl) in enumerate(zip(base_angles, colors, labels)):
        rad = np.radians(angle_deg - 90)   # 画面座標: 0°=上
        cos_a, sin_a = np.cos(rad), np.sin(rad)

        cv2.line(canvas,
                 (cx, cy),
                 (int(cx + max_r * cos_a), int(cy + max_r * sin_a)),
                 (210, 210, 210), 1, cv2.LINE_AA)

        arm_len = int(max_r * snap["servo"][i] / 255)
        ex = int(cx + arm_len * cos_a)
        ey = int(cy + arm_len * sin_a)
        cv2.line(canvas, (cx, cy), (ex, ey), color, 4, cv2.LINE_AA)
        cv2.circle(canvas, (ex, ey), 6, color, -1, cv2.LINE_AA)

        lx = int(cx + (max_r + 20) * cos_a) - 14
        ly = int(cy + (max_r + 20) * sin_a) + 5
        cv2.putText(canvas, f"{lbl}:{snap['servo'][i]}",
                    (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    cv2.putText(canvas, f"r={snap['polar_r']:.1f} th={snap['polar_theta']:.1f}",
                (6, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (30, 120, 30), 1, cv2.LINE_AA)

    return canvas


def _render_servo_chart(snap: dict, w: int, h: int) -> np.ndarray:
    """サーボ値の時系列ラインチャート"""
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)

    cv2.putText(canvas, "SERVO history", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1, cv2.LINE_AA)

    ml, mr, mt, mb = 28, 10, 26, 28   # margin left/right/top/bottom
    cw = w - ml - mr
    ch = h - mt - mb

    # 背景・枠
    cv2.rectangle(canvas, (ml, mt), (ml + cw, mt + ch), (225, 225, 225), -1)
    cv2.rectangle(canvas, (ml, mt), (ml + cw, mt + ch), (170, 170, 170), 1)

    # Y軸グリッド & ラベル (0, 128, 255)
    for val, lbl in [(0, "0"), (128, "128"), (255, "255")]:
        y = mt + ch - int(ch * val / 255)
        cv2.line(canvas, (ml, y), (ml + cw, y), (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(canvas, lbl, (2, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (120, 120, 120), 1, cv2.LINE_AA)

    # ラインチャート描画
    history = snap.get("servo_history", [])
    colors  = [(40, 180, 40), (200, 100, 30), (0, 150, 220)]
    labels  = ["S0", "S1", "S2"]
    n = len(history)
    if n >= 2:
        for si, (color, lbl) in enumerate(zip(colors, labels)):
            pts = [
                (ml + int(cw * t / (SERVO_HISTORY_LEN - 1)),
                 mt + ch - int(ch * history[t][si] / 255))
                for t in range(n)
            ]
            for j in range(1, len(pts)):
                cv2.line(canvas, pts[j - 1], pts[j], color, 2, cv2.LINE_AA)

    # 凡例
    lx = ml + 6
    for color, lbl in zip(colors, labels):
        cv2.line(canvas, (lx, mt + 8), (lx + 14, mt + 8), color, 2, cv2.LINE_AA)
        cv2.putText(canvas, lbl, (lx + 16, mt + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1, cv2.LINE_AA)
        lx += 40

    return canvas


def render_servo_panel(snap: dict, w: int, h: int) -> np.ndarray:
    now = time.time()
    connected = (now - snap["last_hand_t"]) < TIMEOUT_SEC
    half = w // 2
    left  = _render_servo_topview(snap, half, h)
    right = _render_servo_chart(snap, w - half, h)
    panel = np.hstack([left, right])
    _dot(panel, w - 15, 12, connected)
    return panel


# ─────────────────────────────────────────────
#  下段右: チューリップ情報
# ─────────────────────────────────────────────
def render_tulip_panel(snap: dict, w: int, h: int) -> np.ndarray:
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)
    now = time.time()
    connected = (now - snap["last_tulip_t"]) < TIMEOUT_SEC

    _dot(canvas, w - 15, 12, connected)
    cv2.putText(canvas, "TULIP 3D", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1, cv2.LINE_AA)

    # ── 透視投影パラメータ ──────────────────────────────
    Z_MIN, Z_MAX = -0.2, 1.0   # depth_val のクリップ範囲
    hz = Z_MAX - Z_MIN         # ボックスの奥行き = 1.2
    cx, cy = w // 2 - 10, 2 * h // 4
    yaw    = np.radians(35)
    pitch  = np.radians(-35)   # 負 = 上から見下ろす
    cam_d  = 2.2
    scale  = 300

    def proj(x3, y3, z3):
        x1 =  x3 * np.cos(yaw) + z3 * np.sin(yaw)
        z1 = -x3 * np.sin(yaw) + z3 * np.cos(yaw)
        y2 =  y3 * np.cos(pitch) - z1 * np.sin(pitch)
        z2 =  y3 * np.sin(pitch) + z1 * np.cos(pitch)
        zc = max(z2 + cam_d, 0.01)
        return (cx + int(scale * x1 / zc),
                cy - int(scale * y2 / zc))

    def proj_zc(x3, y3, z3):
        """proj と同じ変換で zc (カメラ距離) を返す"""
        z1 = -x3 * np.sin(yaw) + z3 * np.cos(yaw)
        z2 =  y3 * np.sin(pitch) + z1 * np.cos(pitch)
        return max(z2 + cam_d, 0.01)

    # ── ワイヤーフレームボックス ────────────────────────
    hx, hy = 0.75, 0.75
    corners = [
        (-hx, -hy,  0 ), ( hx, -hy,  0 ),
        ( hx,  hy,  0 ), (-hx,  hy,  0 ),
        (-hx, -hy,  hz), ( hx, -hy,  hz),
        ( hx,  hy,  hz), (-hx,  hy,  hz),
    ]
    edges = [(0,1),(1,2),(2,3),(3,0),
             (4,5),(5,6),(6,7),(7,4),
             (0,4),(1,5),(2,6),(3,7)]
    far_set = {4, 5, 6, 7}

    pts2d = [proj(*c) for c in corners]
    for a, b in edges:
        col = (190, 190, 190) if (a in far_set or b in far_set) else (120, 120, 120)
        cv2.line(canvas, pts2d[a], pts2d[b], col, 1, cv2.LINE_AA)

    # ── 軸ラベル ───────────────────────────────────────
    lx = proj(hx + 0.08, -hy, 0)
    cv2.putText(canvas, "X", lx, cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 60, 60), 1, cv2.LINE_AA)
    ly = proj(0, hy + 0.08, 0)
    cv2.putText(canvas, "Y", ly, cv2.FONT_HERSHEY_SIMPLEX, 0.38, (60, 160, 60), 1, cv2.LINE_AA)
    lz = proj(-hx, -hy, hz + 0.15)
    cv2.putText(canvas, "Z(depth)", (lz[0] - 10, lz[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (60, 60, 180), 1, cv2.LINE_AA)

    # ── 軌跡描画 (直近1秒) ────────────────────────────
    def to3d(rx, ry, rd):
        return (rx - 0.5, -(ry - 0.5), Z_MAX - float(np.clip(rd, Z_MIN, Z_MAX)))

    now_t = time.time()
    history = [(rx, ry, rd) for (t, rx, ry, rd) in snap.get("tulip_pos_history", [])
               if now_t - t <= 1.0]
    if len(history) >= 2:
        for i in range(1, len(history)):
            alpha = i / len(history)          # 古い=暗い、新しい=明るい
            col = (int(180 * alpha), int(180 * alpha), int(220 * alpha + 35))
            p1 = proj(*to3d(*history[i - 1]))
            p2 = proj(*to3d(*history[i]))
            cv2.line(canvas, p1, p2, col, 2, cv2.LINE_AA)

    # ── チューリップ位置プロット ──────────────────────
    depth_val = 0.0
    if snap["tulip_detected"]:
        tx = snap["tulip_x"] - 0.5
        ty = -(snap["tulip_y"] - 0.5)
        depth_val = (20 * 4) / snap["tulip_w"] if snap["tulip_w"] > 0 else (Z_MIN + Z_MAX) / 2
        tz = Z_MAX - float(np.clip(depth_val, Z_MIN, Z_MAX))   # Z反転

        tp = proj(tx, ty, tz)

        # 床面への影 (y = -hy)
        fp = proj(tx, -hy, tz)
        cv2.line(canvas, tp, fp, (160, 140, 100), 1, cv2.LINE_AA)
        cv2.circle(canvas, fp, 4, (160, 140, 100), -1, cv2.LINE_AA)

        # 手前面への影 (z = 0)
        sp = proj(tx, ty, 0)
        cv2.line(canvas, tp, sp, (140, 140, 200), 1, cv2.LINE_AA)
        cv2.circle(canvas, sp, 3, (140, 140, 200), -1, cv2.LINE_AA)

        # 本体点 (遠近法: 近いほど大きく)
        zc_val = proj_zc(tx, ty, tz)
        r = max(4, int(12 * cam_d / zc_val))
        cv2.circle(canvas, tp, r + 1, (0, 80, 180),  1, cv2.LINE_AA)
        cv2.circle(canvas, tp, r,     (0, 120, 220), -1, cv2.LINE_AA)

    # ── テキスト情報 ──────────────────────────────────
    yt = h - 38
    cv2.putText(canvas,
                f"x={snap['tulip_x']:.2f}  y={snap['tulip_y']:.2f}  depth={depth_val:.1f}",
                (8, yt), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)
    yt += 18
    cv2.putText(canvas,
                f"conf={snap['tulip_conf']:.2f}  W:{snap['tulip_w']}px  H:{snap['tulip_h']}px",
                (8, yt), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)

    udp_label = "UDP: " + ("LIVE" if connected else "--")
    cv2.putText(canvas, udp_label, (w - 75, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (30, 160, 30) if connected else (40, 40, 200), 1, cv2.LINE_AA)

    return canvas


# ─────────────────────────────────────────────
#  メインループ: 4パネル合成 → imshow
# ─────────────────────────────────────────────
def display_loop(shared: SharedState, stop: threading.Event):
    cv2.namedWindow("Kinetic-Botanics Dashboard", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Kinetic-Botanics Dashboard", WIN_W, WIN_H)

    hand_placeholder  = _make_placeholder("Waiting for hand tracker...",  PANEL_W, PANEL_H)
    tulip_placeholder = _make_placeholder("Waiting for tulip tracker...", PANEL_W, PANEL_H)

    while not stop.is_set():
        snap = shared.snapshot()
        now  = time.time()

        # フレームタイムアウト時はプレースホルダーを使用、余白付きで配置
        if snap["hand_frame"] is None or (now - snap["last_hand_frame_t"]) > TIMEOUT_SEC:
            left_panel = _pad_frame(hand_placeholder)
        else:
            left_panel = _pad_frame(snap["hand_frame"])
            cv2.putText(left_panel, "HAND TRACKING",
                        (FRAME_MARGIN + 8, FRAME_MARGIN + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 240), 2, cv2.LINE_AA)

        if snap["tulip_frame"] is None or (now - snap["last_tulip_frame_t"]) > TIMEOUT_SEC:
            right_panel = _pad_frame(tulip_placeholder)
        else:
            right_panel = _pad_frame(snap["tulip_frame"])
            cv2.putText(right_panel, "TULIP DETECTION",
                        (FRAME_MARGIN + 8, FRAME_MARGIN + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 240), 2, cv2.LINE_AA)

        hand_connected  = snap["hand_detected"]
        tulip_connected = snap["tulip_detected"]
        hand_arrow  = _make_arrow_col(PANEL_H, hand_connected,  now)
        tulip_arrow = _make_arrow_col(PANEL_H, tulip_connected, now)
        hand_row  = np.hstack([left_panel,  hand_arrow,  render_servo_panel(snap, PANEL_W, PANEL_H)])
        tulip_row = np.hstack([right_panel, tulip_arrow, render_tulip_panel(snap, PANEL_W, PANEL_H)])

        canvas = np.vstack([hand_row, tulip_row])

        cv2.imshow("Kinetic-Botanics Dashboard", canvas)

        key = cv2.waitKey(30) & 0xFF
        if key == 27 or key == ord('q'):
            stop.set()
            break

    cv2.destroyAllWindows()


# ─────────────────────────────────────────────
#  エントリポイント
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Kinetic-Botanics Dashboard")
    parser.add_argument("--hand-host",  default="127.0.0.1",
                        help="hand tracker IP (win2 の IPアドレス)")
    parser.add_argument("--tulip-host", default="127.0.0.1",
                        help="tulip tracker IP (mac3 の IPアドレス)")
    args = parser.parse_args()

    hand_url  = f"http://{args.hand_host}:5102/"
    tulip_url = f"http://{args.tulip_host}:5103/"

    shared = SharedState()
    stop   = threading.Event()

    threads = [
        threading.Thread(target=udp_listen_thread,
                         args=(HAND_UDP_PORT,  "hand",  shared, stop), daemon=True),
        threading.Thread(target=udp_listen_thread,
                         args=(TULIP_UDP_PORT, "tulip", shared, stop), daemon=True),
        threading.Thread(target=mjpeg_capture_thread,
                         args=(hand_url,  "hand",  shared, stop), daemon=True),
        threading.Thread(target=mjpeg_capture_thread,
                         args=(tulip_url, "tulip", shared, stop), daemon=True),
    ]

    for t in threads:
        t.start()

    print("Dashboard started. Press ESC or q to quit.")
    print(f"  Hand  JSON  : UDP 0.0.0.0:{HAND_UDP_PORT}")
    print(f"  Tulip JSON  : UDP 0.0.0.0:{TULIP_UDP_PORT}")
    print(f"  Hand  frame : {hand_url}")
    print(f"  Tulip frame : {tulip_url}")

    display_loop(shared, stop)

    stop.set()
    for t in threads:
        t.join(timeout=1.0)


if __name__ == "__main__":
    main()
