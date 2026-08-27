#!/usr/bin/env python3
from pathlib import Path
import re

path = Path("frontend/assets/app.js")
lines = path.read_text().splitlines(keepends=True)

delete_ranges = [
    (205, 260),   # applyMobileChrome through syncSettingsForm (keep loadSettings saveSettings as thin wrappers?)
    (262, 324),   # privacy + readSettingsFromForm
    (339, 435),   # applyHealth + boot
    (442, 510),   # identity card functions
    (517, 520),   # cfg qr/retention + audit refresh (partial)
    (603, 644),   # settings form event listeners
    (726, 791),   # authHeaders + backup events
]

# Keep applyMobileChrome, loadSettings, saveSettings, sleep - thin in app.js
# Actually delete 205-207 applyMobileChrome wrapper - use module in boot
# Keep loadSettings, saveSettings at 211-218

delete_set = set()
for start, end in delete_ranges:
    for i in range(start, end + 1):
        delete_set.add(i)

text = "".join(line for i, line in enumerate(lines, 1) if i not in delete_set)

imports = (
    'import { createAppModesController } from "./modules/app-modes.js";\n'
    'import { createIdentityCardController } from "./modules/identity-card.js";\n'
    'import { createAppHealthController } from "./modules/app-health.js";\n'
    'import { createSettingsFormController } from "./modules/settings-form.js";\n'
    'import { createBootController } from "./modules/app-boot.js";\n'
    'import { createAuditLogController } from "./modules/audit-log.js";\n'
    'import { createIdentityBackupController } from "./modules/identity-backup.js";\n'
)
text = text.replace(
    'import { createAppModesController } from "./modules/app-modes.js";\n',
    imports,
)

text = text.replace(
    "  function applyMobileChrome() {\n    applyMobileChromeModule(settings, els);\n  }\n\n  let settings",
    "  let settings",
)

text = text.replace("    guide.applyGuideMode();\n  }\n\n\n\n  function sleep", "  function sleep")

text = re.sub(
    r'  // Events\n  \$\("#cfgQrOnlyMode"\).*?\n  \$\("#btnAuditRefresh"\).*?\n',
    "  // Events\n",
    text,
    count=1,
)

text = re.sub(
    r'  \[\n    els\.cfgSilhouette,.*?\n  \}\n\n  els\.btnZoneAdd',
    "  els.btnZoneAdd",
    text,
    count=1,
    flags=re.DOTALL,
)

text = re.sub(
    r'\n  async function authHeaders\(\) \{.*?\n  \}\);\n\n  const zones =',
    "\n\n  const zones =",
    text,
    count=1,
    flags=re.DOTALL,
)

# Identity card early init after els
text = text.replace(
    "  const APP_BUILD = globalThis.VIGIEPP_BUILD || \"v47\";\n\n\n  let eppStreak",
    "  const APP_BUILD = globalThis.VIGIEPP_BUILD || \"v48\";\n\n  const identityCard = createIdentityCardController({ els });\n  const { displayPersonName, normalizePersonNameForSave, setIdentityCard } = identityCard;\n\n  function applyMobileChrome() {\n    applyMobileChromeModule(settings, els);\n  }\n\n  let eppStreak",
)

# After audio + ppeProfiles, add settingsForm and health
text = text.replace(
    """  const ppeProfiles = createPpeProfilesController({
    api,
    els,
    settings,
    saveSettings,
  });

  let modes;""",
    """  const ppeProfiles = createPpeProfilesController({
    api,
    els,
    settings,
    saveSettings,
  });

  const auditLog = createAuditLogController({ api });

  let settingsForm;
  let appHealth;
  let bootCtrl;

  let modes;""",
)

# After guide created, settingsForm
text = text.replace(
    """  const guide = createSilhouetteGuideController({
    els,
    settings,
    saveSettings,
    enrollState,
    getAppMode: () => modes.getAppMode(),
  });

  let overlay;""",
    """  const guide = createSilhouetteGuideController({
    els,
    settings,
    saveSettings,
    enrollState,
    getAppMode: () => modes.getAppMode(),
  });

  settingsForm = createSettingsFormController({
    api,
    els,
    settings,
    saveSettings,
    applyGuideMode: guide.applyGuideMode,
    onAudioRepeatsChange: () => audio.resetSpeakIncident(),
  });

  let overlay;""",
)

# Workers use identityCard - already have displayPersonName at top

# After workers, appHealth
text = text.replace(
    """  });

  const detectLive = createDetectLiveController({""",
    """  });

  appHealth = createAppHealthController({
    els,
    enterprise,
    workers,
    setCombinedInference: (v) => { combinedInference = v; },
    setLastHealth: (v) => { lastHealth = v; },
  });
  const { applyHealth } = appHealth;

  const detectLive = createDetectLiveController({""",
)

# modes setConfigSection refreshAudit
text = text.replace("if (id === \"audit\") refreshAudit();", "if (id === \"audit\") auditLog.refreshAudit();")

# After enroll, boot and backup
text = text.replace(
    """  enroll.bindEnrollEvents();

  bindAuthController""",
    """  enroll.bindEnrollEvents();

  bootCtrl = createBootController({
    api,
    els,
    settings,
    ensureAuth,
    applyHealth,
    applyMobileChrome,
    loadSettings,
    ppeProfiles,
    workers,
    teach,
    camera,
    loadZones,
    settingsForm,
    guide,
    modes,
    kiosk,
    buildVersion: APP_BUILD.replace("v", "") ? APP_BUILD.split("v")[1] ? "48" : "48",
  });
  // fix build version
  bootCtrl = createBootController({
    api,
    els,
    settings,
    ensureAuth,
    applyHealth,
    applyMobileChrome,
    loadSettings,
    ppeProfiles,
    workers,
    teach,
    camera,
    loadZones,
    settingsForm,
    guide,
    modes,
    kiosk,
    buildVersion: "48",
  });
  const { boot } = bootCtrl;

  const identityBackup = createIdentityBackupController({ els, workers, ensureAuth });
  identityBackup.bindBackupEvents(downloadUrl);
  auditLog.bindAuditEvents();
  settingsForm.bindSettingsEvents();

  bindAuthController""",
)

# Fix duplicate bootCtrl - simplify insert
text = re.sub(
    r"  bootCtrl = createBootController\(\{[^}]+buildVersion: APP_BUILD.*?\n  \}\);\n  // fix build version\n  bootCtrl = createBootController\(\{",
    "  bootCtrl = createBootController({",
    text,
    count=1,
    flags=re.DOTALL,
)

text = text.replace("  boot();\n", "  boot();\n", 1)

# Remove setCaptureButtonsVisible from enroll
text = text.replace("    setCaptureButtonsVisible,\n", "")

text = text.replace('globalThis.VIGIEPP_BUILD || "v48"', 'globalThis.VIGIEPP_BUILD || "v48"')
text = text.replace("sw.js?v=47", "sw.js?v=48")

path.write_text(text)
print("lines:", text.count("\n"))
