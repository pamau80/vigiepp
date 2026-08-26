/** Detección móvil y viewport. */
import { $ } from "./dom.js";

export const isIOS = () =>
  /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

export const isAndroid = () => /Android/i.test(navigator.userAgent);

export const isMobile = () =>
  isIOS() ||
  isAndroid() ||
  (/Mobile|Opera Mini|IEMobile/i.test(navigator.userAgent) && window.innerWidth < 980) ||
  (navigator.maxTouchPoints > 1 && window.innerWidth < 980);

export function syncViewportHeight() {
  const h = window.visualViewport?.height || window.innerHeight;
  document.documentElement.style.setProperty("--app-vh", `${Math.round(h)}px`);
}

export function applyMobileChrome(settings, els) {
  const mobile = isMobile();
  document.body.classList.toggle("is-mobile", mobile);
  document.body.classList.toggle("is-ios", isIOS());
  document.body.classList.toggle("is-android", isAndroid());
  const hint = $("#speedHint");
  if (mobile) {
    if (els?.chkFullscreen) {
      els.chkFullscreen.checked = false;
      settings.fullscreenDefault = false;
    }
    if (hint) {
      hint.textContent = isIOS()
        ? "iPhone/iPad · Safari o “Agregar a inicio”"
        : "Android · podés instalar como app";
    }
  }
  syncViewportHeight();
}
