import { toast } from "sonner";
import { appendHistory, exportFilename } from "./export-history";
import type { CardProfile } from "../components/CardModal";

export type ExportKind = "csv" | "png" | "pdf" | "card";
export function emitExportBusy(kind: ExportKind, busy: boolean) {
  if (typeof window === "undefined") return;
  (window as any).isGitlyticsExporting = busy;
  window.dispatchEvent(new CustomEvent("gitlytics-export-busy", { detail: { kind, busy } }));
}

function emitStep(message: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("gitlytics-export-step", { detail: { message } }));
}

async function loadLogoImage(): Promise<HTMLImageElement | null> {
  try {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = "/gitlytics-logo.png";
    await new Promise<void>((res, rej) => {
      img.onload = () => res();
      img.onerror = () => rej(new Error("logo"));
    });
    return img;
  } catch {
    return null;
  }
}

async function loadAvatarImage(url: string): Promise<HTMLImageElement | null> {
  try {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = url;
    await new Promise<void>((res, rej) => {
      img.onload = () => res();
      img.onerror = () => rej(new Error("avatar"));
    });
    return img;
  } catch {
    return null;
  }
}

async function drawExportHeader(
  ctx: CanvasRenderingContext2D,
  width: number,
  yOffset: number,
  profile: CardProfile,
  scale: number
) {
  const avatar = profile.avatar_url ? await loadAvatarImage(profile.avatar_url) : null;
  ctx.save();
  const pad = 16 * scale;
  const cardH = 96 * scale;
  const avatarSize = 64 * scale;
  const gap = 16 * scale;
  const x = pad;
  const y = yOffset + pad;
  const w = width - pad * 2;

  ctx.fillStyle = "rgba(15, 15, 20, 0.65)";
  ctx.beginPath();
  if (typeof (ctx as any).roundRect === "function") {
    (ctx as any).roundRect(x, y, w, cardH, 12 * scale);
  } else {
    ctx.rect(x, y, w, cardH);
  }
  ctx.fill();

  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  ctx.lineWidth = 1 * scale;
  ctx.stroke();

  let textX = x + pad * 1.5;

  if (avatar) {
    const avatarX = x + pad * 1.5;
    const avatarY = y + (cardH - avatarSize) / 2;
    const radius = 12 * scale;

    ctx.save();
    ctx.beginPath();
    if (typeof (ctx as any).roundRect === "function") {
      (ctx as any).roundRect(avatarX, avatarY, avatarSize, avatarSize, radius);
    } else {
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
    }
    ctx.clip();
    ctx.drawImage(avatar, avatarX, avatarY, avatarSize, avatarSize);
    ctx.restore();

    ctx.strokeStyle = "#d97757";
    ctx.lineWidth = 1.5 * scale;
    ctx.beginPath();
    if (typeof (ctx as any).roundRect === "function") {
      (ctx as any).roundRect(avatarX, avatarY, avatarSize, avatarSize, radius);
    } else {
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
    }
    ctx.stroke();

    textX = avatarX + avatarSize + gap;
  }

  ctx.textAlign = "left";

  const nameY = y + cardH / 2 - 2 * scale;
  ctx.font = `bold ${22 * scale}px ui-sans-serif, system-ui, -apple-system, sans-serif`;
  ctx.fillStyle = "#ffffff";
  ctx.textBaseline = "bottom";
  ctx.fillText(profile.name, textX, nameY);

  ctx.font = `${14 * scale}px ui-sans-serif, system-ui, -apple-system, sans-serif`;
  ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
  ctx.textBaseline = "top";
  const userText = `@${profile.username}`;
  ctx.fillText(userText, textX, nameY + 2 * scale);

  if (profile.location) {
    const locText = profile.location;
    ctx.font = `${13 * scale}px ui-sans-serif, system-ui, -apple-system, sans-serif`;
    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
    const userW = ctx.measureText(userText).width;
    ctx.textBaseline = "top";
    ctx.fillText(`•  ${locText}`, textX + userW + 10 * scale, nameY + 2 * scale);
  }

  const logo = await loadLogoImage();
  if (logo) {
    const logoSize = 32 * scale;
    const logoX = x + w - pad * 1.5 - logoSize;
    const logoY = y + (cardH - logoSize) / 2;
    ctx.drawImage(logo, logoX, logoY, logoSize, logoSize);
    ctx.font = `bold ${16 * scale}px ui-sans-serif, system-ui, -apple-system, sans-serif`;
    ctx.fillStyle = "#d97757";
    ctx.textBaseline = "middle";
    ctx.textAlign = "right";
    ctx.fillText("Gitlytics", logoX - 8 * scale, y + cardH / 2);
  }
  ctx.restore();
}

function timestampLabel(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Draws a small bottom-right watermark with Gitlytics brand on the given canvas. */
async function drawWatermark(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const logo = await loadLogoImage();
  // Watermark scales with image size so it stays readable on large exports.
  // Smaller, less intrusive watermark — scales gently with export size.
  const scale = Math.max(0.9, Math.min(w, h) / 1600);
  const padX = Math.round(20 * scale);
  const padY = Math.round(18 * scale);
  const logoSize = Math.round(36 * scale);
  const fontWord = Math.round(18 * scale);
  const fontMeta = Math.round(11 * scale);
  ctx.save();
  ctx.globalAlpha = 0.9;
  // wordmark
  ctx.font = `bold ${fontWord}px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto`;
  const git = "Git";
  const lytics = "lytics";
  const gitW = ctx.measureText(git).width;
  const lyticsW = ctx.measureText(lytics).width;
  const wordW = gitW + lyticsW;
  const url = "gitlytics.dev";
  ctx.font = `${fontMeta}px ui-sans-serif, system-ui, -apple-system`;
  const urlW = ctx.measureText(url).width;
  const stamp = timestampLabel();
  const stampW = ctx.measureText(stamp).width;
  const innerPad = Math.round(10 * scale);
  const gap = Math.round(8 * scale);
  const blockW = Math.max(wordW, urlW, stampW) + (logo ? logoSize + gap : 0) + innerPad * 2;
  const blockH = Math.round(62 * scale);
  const x0 = w - blockW - padX;
  const y0 = h - blockH - padY;

  ctx.fillStyle = "rgba(15,15,20,0.72)";
  ctx.beginPath();
  if (typeof (ctx as any).roundRect === "function") {
    (ctx as any).roundRect(x0, y0, blockW, blockH, Math.round(8 * scale));
  } else {
    ctx.rect(x0, y0, blockW, blockH);
  }
  ctx.fill();
  ctx.strokeStyle = "rgba(217,119,87,0.45)";
  ctx.lineWidth = Math.max(1, Math.round(scale));
  ctx.stroke();

  let cursorX = x0 + innerPad;
  const cursorYWord = y0 + innerPad + Math.round(fontWord * 0.85);
  if (logo) {
    ctx.drawImage(logo, cursorX, y0 + (blockH - logoSize) / 2, logoSize, logoSize);
    cursorX += logoSize + gap;
  }
  ctx.font = `bold ${fontWord}px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto`;
  ctx.fillStyle = "#d97757"; // coral — matches --primary
  ctx.fillText(git, cursorX, cursorYWord);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(lytics, cursorX + gitW, cursorYWord);

  ctx.font = `${fontMeta}px ui-sans-serif, system-ui, -apple-system`;
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.fillText(url, cursorX, cursorYWord + Math.round(fontMeta * 1.4));
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.fillText(stamp, cursorX, cursorYWord + Math.round(fontMeta * 2.6));
  ctx.restore();
}

function bgColor() {
  if (typeof window === "undefined") return "#000";
  return getComputedStyle(document.body).backgroundColor || "#000";
}

async function loadHtml2Canvas() {
  return (await import("html2canvas-pro")).default;
}

/** Inject temp CSS so chart Y-axis labels aren't clipped during capture. */
function applyExportCss(): () => void {
  const style = document.createElement("style");
  style.setAttribute("data-gitlytics-export", "1");
  style.textContent = `
    .recharts-wrapper, .recharts-surface { overflow: visible !important; }
    .recharts-responsive-container { overflow: visible !important; }
    .recharts-cartesian-axis-tick text { font-size: 11px; }
    [id^="section-"], #dashboard-root .glass { overflow: visible !important; }
    #dashboard-root * {
      animation-delay: 0s !important;
      animation-duration: 0s !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0s !important;
      transition-delay: 0s !important;
    }
  `;
  document.head.appendChild(style);
  return () => style.remove();
}

export async function runPngExport(sectionIds: string[], repoLabel = "All repos", profile?: CardProfile) {
  if (sectionIds.length === 0) return;
  emitExportBusy("png", true);
  const tid = toast.loading("Generating PNG…");
  // Force expand collapsible rows (e.g. RepoTable, UsernameView rows) for capture.
  window.dispatchEvent(new CustomEvent("gitlytics-export-expand"));
  const cleanupCss = applyExportCss();
  try {
    emitStep("Preparing sections…");
    const html2canvas = await loadHtml2Canvas();
    const bg = bgColor();
    const opts = { scale: 2, useCORS: true, allowTaint: true, backgroundColor: bg };
    emitStep("Rendering charts…");
    await new Promise((r) => setTimeout(r, 1500));
    emitStep("Capturing dashboard…");
    const canvases: HTMLCanvasElement[] = [];
    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (!el) continue;
      // Scroll element into view so lazy charts mount, then wait a frame.
      el.scrollIntoView({ block: "center", behavior: "instant" as ScrollBehavior });
      await new Promise((r) => setTimeout(r, 250));
      const rect = el.getBoundingClientRect();
      canvases.push(
        await html2canvas(el, {
          ...opts,
          width: Math.ceil(rect.width),
          height: Math.ceil(el.scrollHeight),
          windowWidth: document.documentElement.clientWidth,
        }),
      );
    }
    if (canvases.length === 0) throw new Error("No sections found");
    const gap = 32;
    const width = Math.max(...canvases.map((c) => c.width));
    const headerH = profile ? (96 + 32) * 2 : 0;
    const totalH =
      canvases.reduce((a, c) => a + c.height, 0) +
      gap * (canvases.length - 1) +
      gap * 2 +
      (profile ? headerH + gap : 0);
    const out = document.createElement("canvas");
    out.width = width + gap * 2;
    out.height = totalH;
    const ctx = out.getContext("2d")!;
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, out.width, out.height);
    let y = gap;
    if (profile) {
      emitStep("Adding profile header…");
      await drawExportHeader(ctx, out.width, y, profile, 2);
      y += headerH + gap;
    }
    for (const c of canvases) {
      ctx.drawImage(c, gap, y);
      y += c.height + gap;
    }
    emitStep("Adding watermark…");
    await drawWatermark(ctx, out.width, out.height);
    emitStep("Generating file…");
    const filename = exportFilename("png");
    const a = document.createElement("a");
    a.href = out.toDataURL("image/png");
    a.download = filename;
    a.click();
    appendHistory({ action: "Export PNG", repos: repoLabel, filename });
    toast.success("PNG ready — downloading", { id: tid, duration: 3000 });
  } catch (e) {
    toast.error("Failed to generate PNG", { id: tid });
    throw e;
  } finally {
    cleanupCss();
    window.dispatchEvent(new CustomEvent("gitlytics-export-restore"));
    emitExportBusy("png", false);
  }
}

/**
 * Multi-page PDF using JPEG-encoded page slices.
 * Previous implementation embedded a single full-height PNG (often 100MB+).
 * This slices the source canvas page-by-page into JPEG (q=0.82) — ~3-10MB.
 */
export async function runPdfExport(repoLabel = "All repos", profile?: CardProfile) {
  emitExportBusy("pdf", true);
  const tid = toast.loading("Generating full report… this may take a few seconds");
  window.dispatchEvent(new CustomEvent("gitlytics-export-expand"));
  const cleanupCss = applyExportCss();
  try {
    emitStep("Preparing full report…");
    emitStep("Expanding all sections…");
    await new Promise((r) => setTimeout(r, 900));
    emitStep("Rendering all charts…");
    await new Promise((r) => setTimeout(r, 2000));
    const html2canvas = await loadHtml2Canvas();
    const { jsPDF } = await import("jspdf");
    const bg = bgColor();
    const root = document.getElementById("dashboard-root") || document.body;
    const SCALE = 1.5;
    emitStep("Capturing dashboard…");
    const source = await html2canvas(root, {
      scale: SCALE,
      useCORS: true,
      allowTaint: true,
      backgroundColor: bg,
      windowHeight: document.documentElement.scrollHeight,
      height: root.scrollHeight,
    });

    let finalSource = source;
    if (profile) {
      emitStep("Adding profile header…");
      const headerH = (96 + 32) * SCALE;
      const combined = document.createElement("canvas");
      combined.width = source.width;
      combined.height = source.height + headerH;
      const cctx = combined.getContext("2d")!;
      cctx.fillStyle = bg;
      cctx.fillRect(0, 0, combined.width, combined.height);
      await drawExportHeader(cctx, combined.width, 0, profile, SCALE);
      cctx.drawImage(source, 0, headerH);
      finalSource = combined;
    }

    const pdf = new jsPDF("l", "mm", "a4");
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();

    // pixels per mm in our source canvas
    const pxPerMm = finalSource.width / pageW;
    const pageSlicePx = Math.floor(pageH * pxPerMm);

    const slice = document.createElement("canvas");
    slice.width = finalSource.width;
    slice.height = pageSlicePx;
    const sctx = slice.getContext("2d")!;

    emitStep("Adding watermark…");
    emitStep("Building PDF…");
    let offset = 0;
    let pageIndex = 0;
    while (offset < finalSource.height) {
      const h = Math.min(pageSlicePx, finalSource.height - offset);
      slice.height = h;
      sctx.fillStyle = bg;
      sctx.fillRect(0, 0, slice.width, h);
      sctx.drawImage(finalSource, 0, offset, finalSource.width, h, 0, 0, finalSource.width, h);
      await drawWatermark(sctx, slice.width, h);
      const img = slice.toDataURL("image/jpeg", 0.82);
      const renderH = (h / pxPerMm);
      if (pageIndex > 0) pdf.addPage();
      pdf.addImage(img, "JPEG", 0, 0, pageW, renderH, undefined, "FAST");
      offset += h;
      pageIndex += 1;
    }

    const filename = exportFilename("pdf");
    pdf.save(filename);
    appendHistory({ action: "Export PDF", repos: repoLabel, filename });
    toast.success("PDF ready — downloading", { id: tid, duration: 3000 });
  } catch (e) {
    toast.error("Failed to generate PDF", { id: tid });
    throw e;
  } finally {
    cleanupCss();
    window.dispatchEvent(new CustomEvent("gitlytics-export-restore"));
    emitExportBusy("pdf", false);
  }
}

export async function runCardExport(username: string) {
  emitExportBusy("card", true);
  const tid = toast.loading("Generating card…");
  try {
    emitStep("Preparing card…");
    emitStep("Rendering…");
    await new Promise((r) => setTimeout(r, 1000));
    const html2canvas = await loadHtml2Canvas();
    const el = document.getElementById("developer-card");
    if (!el) throw new Error("Card not found");
    const bg = bgColor();
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: null,
    });
    emitStep("Adding branding…");
    await drawWatermark(canvas.getContext("2d")!, canvas.width, canvas.height);
    emitStep("Downloading…");
    const filename = exportFilename("card", username);
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = filename;
    a.click();
    appendHistory({ action: "Create Card", repos: `@${username}`, filename });
    toast.success("Card ready — downloading", { id: tid, duration: 3000 });
  } catch (e) {
    toast.error("Failed to generate card", { id: tid });
    throw e;
  } finally {
    emitExportBusy("card", false);
  }
}
