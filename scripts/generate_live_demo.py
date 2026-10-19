import asyncio
import os
import subprocess
import sys
import time
from playwright.async_api import async_playwright

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

CURSOR_JS = """
() => {
  if (document.getElementById('demo-cursor')) return;
  const cursor = document.createElement('div');
  cursor.id = 'demo-cursor';
  Object.assign(cursor.style, {
    position: 'fixed', top: '0px', left: '0px',
    width: '20px', height: '20px',
    background: 'rgba(239, 68, 68, 0.9)',
    border: '2px solid white', borderRadius: '50%',
    boxShadow: '0 0 14px rgba(239, 68, 68, 0.7)',
    pointerEvents: 'none', zIndex: '999999',
    transition: 'transform 0.2s cubic-bezier(0.22, 1, 0.36, 1)',
    transform: 'translate(-50%, -50%)'
  });
  document.body.appendChild(cursor);

  document.addEventListener('mousemove', e => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
  });
  document.addEventListener('mousedown', e => {
    cursor.style.transform = 'translate(-50%, -50%) scale(0.65)';
    const ripple = document.createElement('div');
    Object.assign(ripple.style, {
      position: 'fixed', left: e.clientX + 'px', top: e.clientY + 'px',
      width: '12px', height: '12px', borderRadius: '50%',
      border: '2.5px solid rgba(239, 68, 68, 0.95)',
      transform: 'translate(-50%, -50%) scale(1)',
      opacity: '1', pointerEvents: 'none', zIndex: '999998',
      transition: 'all 0.5s ease-out'
    });
    document.body.appendChild(ripple);
    requestAnimationFrame(() => {
      ripple.style.transform = 'translate(-50%, -50%) scale(4.5)';
      ripple.style.opacity = '0';
    });
    setTimeout(() => ripple.remove(), 500);
  });
  document.addEventListener('mouseup', () => {
    cursor.style.transform = 'translate(-50%, -50%) scale(1)';
  });
}
"""

async def smooth_move_to_loc(page, selector: str, steps: int = 30, pause_after: float = 0.5):
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=6000)
        box = await loc.bounding_box()
        if box:
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2
            await page.mouse.move(target_x, target_y, steps=steps)
            await asyncio.sleep(pause_after)
    except Exception as e:
        print(f"Warning in smooth_move_to_loc({selector}): {e}")

async def smooth_click(page, selector: str, steps: int = 30, pause_after: float = 1.0):
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=6000)
        await loc.scroll_into_view_if_needed()
        box = await loc.bounding_box()
        if box:
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2
            await page.mouse.move(target_x, target_y, steps=steps)
            await asyncio.sleep(0.3)
            await page.mouse.click(target_x, target_y)
        else:
            await loc.click()
    except Exception as e:
        print(f"Warning in smooth_click({selector}): {e}")
    await asyncio.sleep(pause_after)

async def smooth_scroll_by(page, delta_y: int, steps: int = 25, pause_after: float = 0.5):
    step_y = delta_y / steps
    for _ in range(steps):
        await page.evaluate(f"window.scrollBy(0, {step_y})")
        await asyncio.sleep(0.03)
    await asyncio.sleep(pause_after)

async def record_video():
    app_url = "https://pharos-arbitrage-scanner.vercel.app"
    os.makedirs("./raw_video", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir="./raw_video",
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        print("Navigating to production URL:", app_url, flush=True)
        await page.goto(app_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2.0)
        await page.evaluate(CURSOR_JS)
        await asyncio.sleep(1.0)

        start_time = time.time()
        print("Starting synchronized recording workflow...")

        # ---------------------------------------------------------
        # PART 1: Introduction (0.0s to ~19.0s, total target ~19.0s)
        # ---------------------------------------------------------
        print("[Part 1] Introducing Pharos Arbitrage Scanner...")
        # Move cursor to top announcement banner
        await page.mouse.move(960, 20, steps=30)
        await asyncio.sleep(3.0)
        # Hover over the header brand & title
        await smooth_move_to_loc(page, "h1", steps=30, pause_after=3.5)
        # Hover over version badge v0.2.0
        await smooth_move_to_loc(page, "span:has-text('v0.2.0')", steps=20, pause_after=2.5)
        # Hover over network badge #688689
        await smooth_move_to_loc(page, "#networkBadge", steps=25, pause_after=3.0)
        # Hover over live gas display
        await smooth_move_to_loc(page, "#liveGasDisplay", steps=20, pause_after=3.5)

        # Ensure Part 1 hits ~19.0s mark
        elapsed = time.time() - start_time
        if elapsed < 19.0:
            await asyncio.sleep(19.0 - elapsed)

        # ---------------------------------------------------------
        # PART 2: Live Application & On-Chain Audit (19.0s to ~45.0s)
        # ---------------------------------------------------------
        print("[Part 2] Demonstrating live network status and on-chain indicators...")
        # Click the 'Query Nodes' button
        await smooth_click(page, "#btnManualRefresh", steps=25, pause_after=3.0)

        # Glide over the verified reference oracle cards
        await smooth_move_to_loc(page, "#feedBtcPrice", steps=25, pause_after=2.5)
        await smooth_move_to_loc(page, "#feedEthPrice", steps=25, pause_after=2.5)
        await smooth_move_to_loc(page, "#feedProsPrice", steps=25, pause_after=2.5)

        # Scroll down to Section 2: On-Chain DEX Deployments
        await smooth_scroll_by(page, 280, steps=25, pause_after=1.0)
        # Hover over FaroSwap DEX Card (Mainnet Chain 1672)
        await smooth_move_to_loc(page, "h2:has-text('FaroSwap DEX')", steps=25, pause_after=2.5)
        await smooth_move_to_loc(page, "#faroswapPairsCount", steps=20, pause_after=2.5)
        await smooth_move_to_loc(page, "div:has-text('0 Deployed (No 2nd Venue)')", steps=20, pause_after=2.5)

        # Hover over Atlantic Testnet Card (Chain 688689)
        await smooth_move_to_loc(page, "h2:has-text('AMM Pools · Atlantic Testnet')", steps=25, pause_after=2.5)
        await smooth_move_to_loc(page, "div:has-text('LOCKED (Fail-Closed)')", steps=20, pause_after=2.5)

        elapsed = time.time() - start_time
        if elapsed < 45.0:
            await asyncio.sleep(45.0 - elapsed)

        # ---------------------------------------------------------
        # PART 3: Scanning and Audit Trail (45.0s to ~79.5s)
        # ---------------------------------------------------------
        print("[Part 3] Demonstrating Live Scan workflow and audit trail...")
        # Scroll to Section 3: Live Scanner
        await smooth_scroll_by(page, 340, steps=25, pause_after=1.0)

        # Scan 1: BTC/USD
        await smooth_move_to_loc(page, "#selectPair", steps=20, pause_after=1.5)
        await smooth_click(page, "#btnRunScan", steps=20, pause_after=3.5)

        # Scan 2: ETH/USD
        await smooth_click(page, "#selectPair", steps=20, pause_after=0.5)
        await page.select_option("#selectPair", "ETH/USD")
        await asyncio.sleep(1.0)
        await smooth_click(page, "#btnRunScan", steps=20, pause_after=3.5)

        # Scan 3: PROS/USD
        await smooth_click(page, "#selectPair", steps=20, pause_after=0.5)
        await page.select_option("#selectPair", "PROS/USD")
        await asyncio.sleep(1.0)
        await smooth_click(page, "#btnRunScan", steps=20, pause_after=3.5)

        # Inspect table rows
        await smooth_move_to_loc(page, "#scanHistoryBody tr:first-child", steps=25, pause_after=3.0)
        await smooth_move_to_loc(page, "#scanHistoryBody span:has-text('LIVE_ARBITRAGE_UNAVAILABLE_NO_VERIFIED_LIQUIDITY')", steps=20, pause_after=4.0)

        elapsed = time.time() - start_time
        if elapsed < 79.5:
            await asyncio.sleep(79.5 - elapsed)

        # ---------------------------------------------------------
        # PART 4: Profitability Analysis & AMM Sandbox (79.5s to ~107.4s)
        # ---------------------------------------------------------
        print("[Part 4] Explaining Constant-Product AMM Math & Waterfall deductions...")
        # Scroll down to Section 4: Pure Mathematical Engine
        await smooth_scroll_by(page, 440, steps=25, pause_after=1.0)

        # Hover over Mathematical Engine badge
        await smooth_move_to_loc(page, "span:has-text('MATHEMATICAL ENGINE')", steps=20, pause_after=2.0)

        # Test Scenario 1: Wide Spread
        await smooth_click(page, "button[data-scenario='wide_spread']", steps=20, pause_after=2.5)
        await smooth_move_to_loc(page, "#wfGrossSpread", steps=15, pause_after=1.5)
        await smooth_move_to_loc(page, "#wfLpFees", steps=15, pause_after=1.5)
        await smooth_move_to_loc(page, "#wfSlippage", steps=15, pause_after=1.5)
        await smooth_move_to_loc(page, "#wfNetProfit", steps=15, pause_after=2.0)

        # Test Scenario 2: Slippage Erosion
        await smooth_click(page, "button[data-scenario='slippage_eroded']", steps=20, pause_after=3.0)
        await smooth_move_to_loc(page, "#wfSlippage", steps=15, pause_after=1.5)
        await smooth_move_to_loc(page, "#wfNetProfit", steps=15, pause_after=2.0)

        # Test Scenario 3: Inverted Spread
        await smooth_click(page, "button[data-scenario='inverted_spread']", steps=20, pause_after=3.0)
        await smooth_move_to_loc(page, "#detailStatusBadge", steps=15, pause_after=2.0)

        # Reset to Wide Spread and adjust volume slider
        await smooth_click(page, "button[data-scenario='wide_spread']", steps=15, pause_after=1.5)
        await smooth_move_to_loc(page, "#inputVolume", steps=20, pause_after=1.0)
        
        # Drag volume slider
        box = await page.locator("#inputVolume").bounding_box()
        if box:
            slider_y = box["y"] + box["height"] / 2
            await page.mouse.click(box["x"] + box["width"] * 0.25, slider_y)
            await asyncio.sleep(1.0)
            await page.mouse.click(box["x"] + box["width"] * 0.65, slider_y)
            await asyncio.sleep(1.5)

        elapsed = time.time() - start_time
        if elapsed < 107.4:
            await asyncio.sleep(107.4 - elapsed)

        # ---------------------------------------------------------
        # PART 5: Safety and Limitations (107.4s to ~129.5s)
        # ---------------------------------------------------------
        print("[Part 5] Highlighting fail-closed safety controls and zero-mock guarantee...")
        # Smoothly scroll all the way back up to the Primary Status Alert
        await smooth_scroll_by(page, -900, steps=30, pause_after=1.0)
        await smooth_move_to_loc(page, "span:has-text('PRODUCTION STATUS: FAIL-CLOSED')", steps=25, pause_after=3.0)
        await smooth_move_to_loc(page, "span:has-text('0 Actionable Opportunities')", steps=25, pause_after=3.0)
        await smooth_move_to_loc(page, "span:has-text('Zero Simulated Trades · Fail-Closed Execution Lock')", steps=25, pause_after=4.0)

        elapsed = time.time() - start_time
        if elapsed < 129.5:
            await asyncio.sleep(129.5 - elapsed)

        # ---------------------------------------------------------
        # PART 6: Conclusion (129.5s to ~147.5s)
        # ---------------------------------------------------------
        print("[Part 6] Conclusion, public links, and repository...")
        # Scroll down to footer
        await smooth_scroll_by(page, 950, steps=25, pause_after=1.0)
        await smooth_move_to_loc(page, "a[href*='github.com']", steps=25, pause_after=3.0)
        await smooth_move_to_loc(page, "a[href*='ai.pharos.xyz']", steps=20, pause_after=2.5)
        await smooth_move_to_loc(page, "a[href*='atlantic.pharosscan.xyz']", steps=20, pause_after=2.5)

        # Return to top header for clean sign-off
        await smooth_scroll_by(page, -950, steps=25, pause_after=1.0)
        await smooth_move_to_loc(page, "h1", steps=25, pause_after=2.0)

        elapsed = time.time() - start_time
        target_total = 147.5
        if elapsed < target_total:
            await asyncio.sleep(target_total - elapsed)

        print(f"Workflow completed! Total recording duration: {time.time() - start_time:.2f}s", flush=True)
        video_obj = page.video
        await page.close()
        await context.close()
        await browser.close()
        video_path = await video_obj.path()
        print(f"Video saved to: {video_path}", flush=True)
        return video_path

def merge_video(webm_path: str):
    audio_path = "final_voiceover.mp3"
    output_mp4 = "demo/pharos_arbitrage_scanner_demo.mp4"
    print(f"Merging {webm_path} and {audio_path} into {output_mp4} using FFmpeg...")

    cmd = [
        "ffmpeg", "-y",
        "-i", webm_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_mp4
    ]
    subprocess.run(cmd, check=True)
    print("Video rendering finished successfully!")
    return output_mp4

async def main():
    webm_path = await record_video()
    print("Recorded raw WebM:", webm_path)
    output_mp4 = merge_video(webm_path)
    print("Final MP4 produced at:", output_mp4)

if __name__ == "__main__":
    asyncio.run(main())
