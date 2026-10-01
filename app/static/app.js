(() => {
  const pageBody = document.body;
  const motionLevel = pageBody.dataset.motionLevel || "full";
  const mathEnabled = pageBody.dataset.renderMath === "true";
  const reduceMotionPreference = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const effectiveMotionLevel = reduceMotionPreference ? "minimal" : motionLevel;
  const motionProfile =
    {
      full: {
        loaderFirstDuration: 2.4,
        loaderRepeatDuration: 1.2,
        loaderFirstVisibleMs: 2400,
        loaderRepeatVisibleMs: 1300,
        countDuration: 1.1,
        revealDuration: 0.55,
        revealYOffset: 26,
      },
      soft: {
        loaderFirstDuration: 1.9,
        loaderRepeatDuration: 1,
        loaderFirstVisibleMs: 1850,
        loaderRepeatVisibleMs: 1100,
        countDuration: 0.85,
        revealDuration: 0.42,
        revealYOffset: 18,
      },
      minimal: {
        loaderFirstDuration: 1.1,
        loaderRepeatDuration: 0.75,
        loaderFirstVisibleMs: 1200,
        loaderRepeatVisibleMs: 900,
        countDuration: 0,
        revealDuration: 0,
        revealYOffset: 0,
      },
    }[effectiveMotionLevel] || {
      loaderFirstDuration: 2.4,
      loaderRepeatDuration: 1.2,
      loaderFirstVisibleMs: 2400,
      loaderRepeatVisibleMs: 1300,
      countDuration: 1.1,
      revealDuration: 0.55,
      revealYOffset: 26,
    };
  const loader = document.getElementById("loader-screen");
  const progressFill = document.getElementById("loader-progress-fill");
  const progressText = document.getElementById("loader-progress-text");
  const progressLabel = document.getElementById("loader-status-label");
  const loaderSteps = Array.from(document.querySelectorAll("[data-loader-step]"));
  const loaderSeen = sessionStorage.getItem("ls-loader-seen") === "true";
  const loaderMessages = [
    "正在同步任务总图",
    "正在映射学习通道",
    "正在生成复习检查点",
    "正在打开今天的控制台",
  ];

  loaderMessages.splice(
    0,
    loaderMessages.length,
    "正在同步任務總覽",
    "正在映射學習路徑",
    "正在生成複習節點",
    "正在打開今天的控制台",
  );

  function initLoader() {
    if (!loader || !window.gsap) {
      if (loader) {
        loader.remove();
      }
      setPageReady();
      animatePage();
      return;
    }

    const progressState = { value: 0 };
    const targetDuration = loaderSeen
      ? motionProfile.loaderRepeatDuration
      : motionProfile.loaderFirstDuration;
    const minimumVisibleMs = loaderSeen
      ? motionProfile.loaderRepeatVisibleMs
      : motionProfile.loaderFirstVisibleMs;
    const startTime = performance.now();

    const progressTween = gsap.to(progressState, {
      value: 100,
      duration: targetDuration,
      ease: "power2.out",
      onUpdate: () => {
        const value = Math.round(progressState.value);
        const stepIndex = Math.min(loaderSteps.length - 1, Math.floor(value / 34));
        progressFill.style.width = `${value}%`;
        progressText.textContent = `${value}%`;
        progressLabel.textContent = loaderMessages[Math.min(loaderMessages.length - 1, Math.floor(value / 26))];
        loaderSteps.forEach((step, index) => {
          step.classList.toggle("is-active", index <= stepIndex);
        });
      },
    });

    const closeLoader = () => {
      progressTween.progress(1);

      const tl = gsap.timeline({
        defaults: { ease: "power3.inOut" },
        onComplete: () => {
          loader.remove();
          sessionStorage.setItem("ls-loader-seen", "true");
          animatePage();
        },
      });

      gsap.delayedCall(0.14, setPageReady);

      tl.to(".loader-core", { autoAlpha: 0, y: -12, scale: 0.97, duration: 0.38 })
        .to(".loader-door-top", { yPercent: -100, duration: 0.85 }, 0)
        .to(".loader-door-bottom", { yPercent: 100, duration: 0.85 }, 0)
        .to(loader, { autoAlpha: 0, duration: 0.3 }, "-=0.2");
    };

    const ready = () => {
      const elapsed = performance.now() - startTime;
      const remainingDelay = Math.max(0, minimumVisibleMs - elapsed);
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => {
          window.setTimeout(closeLoader, remainingDelay);
        });
      } else {
        window.setTimeout(closeLoader, remainingDelay);
      }
    };

    if (document.readyState === "complete") {
      ready();
    } else {
      window.addEventListener("load", ready, { once: true });
    }
  }

  function animateCountUps() {
    if (!window.gsap || effectiveMotionLevel === "minimal") {
      return;
    }

    document.querySelectorAll(".count-up").forEach((element) => {
      const target = Number(element.dataset.value);
      if (!Number.isFinite(target)) {
        return;
      }

      const state = { value: 0 };
      gsap.to(state, {
        value: target,
        duration: motionProfile.countDuration,
        ease: "power3.out",
        onUpdate: () => {
          element.textContent = Math.round(state.value).toLocaleString();
        },
      });
    });
  }

  function animatePage() {
    if (!window.gsap) {
      queueMathTypeset();
      return;
    }

    animateCountUps();

    if (effectiveMotionLevel === "minimal") {
      queueMathTypeset();
      return;
    }

    if (window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
    }

    if (window.ScrollTrigger) {
      const viewportThreshold = window.innerHeight * 0.84;
      gsap.utils
        .toArray(".panel, .task-card, .resource-card, .unit-card, .micro-step, .protocol-card, .note-tile")
        .forEach((item) => {
          if (item.getBoundingClientRect().top < viewportThreshold) {
            return;
          }
          gsap.from(item, {
            y: motionProfile.revealYOffset,
            autoAlpha: 0,
            duration: motionProfile.revealDuration,
            ease: "power2.out",
            scrollTrigger: {
              trigger: item,
              start: "top 88%",
              once: true,
            },
          });
        });
    }

    const rings = document.querySelectorAll(".orbit-ring");
    if (rings[0]) {
      gsap.to(rings[0], { rotate: 360, repeat: -1, duration: 18, ease: "none" });
    }
    if (rings[1]) {
      gsap.to(rings[1], { rotate: -360, repeat: -1, duration: 26, ease: "none" });
    }
    if (document.querySelector(".pulse-core")) {
      gsap.to(".pulse-core", { scale: 1.03, repeat: -1, yoyo: true, duration: 2.2, ease: "sine.inOut" });
    }

    queueMathTypeset();
  }

  function initMagneticButtons() {
    if (
      effectiveMotionLevel !== "full" ||
      !window.matchMedia("(hover: hover) and (pointer: fine)").matches ||
      !window.gsap
    ) {
      return;
    }

    document.querySelectorAll(".magnetic-button").forEach((button) => {
      const strength = 18;
      button.addEventListener("mousemove", (event) => {
        const rect = button.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;
        gsap.to(button, {
          x: x / strength,
          y: y / strength,
          duration: 0.28,
          ease: "power3.out",
        });
      });

      button.addEventListener("mouseleave", () => {
        gsap.to(button, { x: 0, y: 0, duration: 0.35, ease: "power3.out" });
      });
    });
  }

  function initHeaderBehavior() {
    const header = document.getElementById("site-header");
    if (!header) {
      return;
    }

    const syncHeaderState = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 24);
    };

    syncHeaderState();
    window.addEventListener("scroll", syncHeaderState, { passive: true });
  }

  function initPointerGlow() {
    if (
      effectiveMotionLevel === "minimal" ||
      !window.matchMedia("(hover: hover) and (pointer: fine)").matches
    ) {
      return;
    }

    const root = document.documentElement;
    let targetX = window.innerWidth * 0.5;
    let targetY = window.innerHeight * 0.2;
    let currentX = targetX;
    let currentY = targetY;
    let frameHandle = 0;
    let lastMoveAt = performance.now();

    const applyPointer = () => {
      const dx = targetX - currentX;
      const dy = targetY - currentY;
      currentX += dx * 0.16;
      currentY += dy * 0.16;

      const energy = Math.min(1, Math.hypot(dx, dy) / 36);
      root.style.setProperty("--pointer-x", `${currentX}px`);
      root.style.setProperty("--pointer-y", `${currentY}px`);
      root.style.setProperty("--pointer-glow-opacity", `${(0.56 + energy * 0.16).toFixed(3)}`);

      const isIdle = performance.now() - lastMoveAt > 140 && Math.hypot(dx, dy) < 0.18;
      if (isIdle) {
        frameHandle = 0;
        return;
      }

      frameHandle = window.requestAnimationFrame(applyPointer);
    };

    root.style.setProperty("--pointer-x", `${currentX}px`);
    root.style.setProperty("--pointer-y", `${currentY}px`);

    window.addEventListener(
      "mousemove",
      (event) => {
        targetX = event.clientX;
        targetY = event.clientY;
        lastMoveAt = performance.now();
        if (!frameHandle) {
          frameHandle = window.requestAnimationFrame(applyPointer);
        }
      },
      { passive: true },
    );
  }

  function initExpandableSections() {
    document.querySelectorAll("[data-expander]").forEach((expander) => {
      const toggle = expander.querySelector("[data-expander-toggle]");
      const body = expander.querySelector("[data-expander-body]");
      if (!toggle || !body) {
        return;
      }

      const syncState = (isOpen) => {
        toggle.setAttribute("aria-expanded", String(isOpen));
        expander.classList.toggle("is-open", isOpen);
        body.hidden = !isOpen;
      };

      syncState(toggle.getAttribute("aria-expanded") === "true" && !body.hidden);

      toggle.addEventListener("click", () => {
        const willOpen = toggle.getAttribute("aria-expanded") !== "true";
        syncState(willOpen);
        if (willOpen) {
          queueMathTypeset([body]);
        }
      });
    });
  }

  function initSubmitLoaders() {
    document.querySelectorAll("form[data-loading-submit]").forEach((form) => {
      if (form.dataset.loadingBound === "true") {
        return;
      }
      form.dataset.loadingBound = "true";

      const overlay = form.querySelector("[data-submit-loader]");
      const submitControls = Array.from(form.querySelectorAll("button[type='submit'], input[type='submit']"));
      const fallbackText = form.dataset.loadingText || "正在處理，請稍候...";
      const statusLabel = form.querySelector("[data-import-status-label]");
      const statusDetail = form.querySelector("[data-import-status-detail]");
      const progressFill = form.querySelector("[data-import-progress-fill]");
      const progressText = form.querySelector("[data-import-progress-text]");
      const activeJobId = form.dataset.activeImportJobId || "";
      let pollHandle = 0;
      let consecutivePollFailures = 0;
      const maxTransientPollFailures = 6;

      const setSubmittingState = (isSubmitting) => {
        form.classList.toggle("is-submitting", isSubmitting);
        if (overlay) {
          overlay.hidden = !isSubmitting;
        }
      };

      const setProgress = (percent, label, detail) => {
        const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
        if (progressFill) {
          progressFill.style.width = `${safePercent}%`;
        }
        if (progressText) {
          progressText.textContent = `${Math.round(safePercent)}%`;
        }
        if (statusLabel && label) {
          statusLabel.textContent = label;
        }
        if (statusDetail && detail) {
          statusDetail.textContent = detail;
        }
      };

      const setControlsDisabled = (disabled) => {
        submitControls.forEach((control) => {
          const loadingText = control.dataset.loadingText || fallbackText;
          control.disabled = disabled;
          control.setAttribute("aria-busy", disabled ? "true" : "false");

          if (control instanceof HTMLInputElement) {
            control.value = disabled ? loadingText : (control.dataset.originalValue || control.defaultValue || control.value);
            return;
          }

          if (!control.dataset.originalText) {
            control.dataset.originalText = control.textContent || "";
          }
          control.textContent = disabled ? loadingText : control.dataset.originalText;
        });
      };

      const stopPolling = () => {
        if (pollHandle) {
          window.clearTimeout(pollHandle);
          pollHandle = 0;
        }
      };

      const setActiveJobInUrl = (jobId) => {
        const nextUrl = new URL(window.location.href);
        if (jobId) {
          nextUrl.searchParams.set("job", jobId);
        } else {
          nextUrl.searchParams.delete("job");
        }
        window.history.replaceState({}, "", nextUrl.toString());
      };

      const finishPollingWithMessage = (message) => {
        stopPolling();
        setControlsDisabled(false);
        setSubmittingState(false);
        if (statusDetail) {
          statusDetail.textContent = message;
        }
      };

      const pollJob = async (jobId) => {
        stopPolling();
        setSubmittingState(true);
        setControlsDisabled(true);

        try {
          const response = await fetch(`/imports/${encodeURIComponent(jobId)}`, {
            headers: {
              Accept: "application/json",
            },
            cache: "no-store",
          });
          if (!response.ok) {
            throw new Error("無法取得匯入狀態。");
          }
          const job = await response.json();
          setProgress(job.progress_percent, job.status_label, job.detail || job.error_message || "");

          if (job.status === "completed" && job.resource_id) {
            window.location.href = `/resources/${encodeURIComponent(job.resource_id)}`;
            return;
          }
          if (job.status === "failed") {
            setControlsDisabled(false);
            stopPolling();
            if (statusDetail) {
              statusDetail.textContent = job.error_message || job.detail || "匯入失敗。";
            }
            return;
          }

          pollHandle = window.setTimeout(() => {
            void pollJob(jobId);
          }, 1200);
        } catch (error) {
          setControlsDisabled(false);
          stopPolling();
          if (statusDetail) {
            statusDetail.textContent = error instanceof Error ? error.message : "匯入狀態輪詢失敗。";
          }
        }
      };

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setSubmittingState(true);
        setControlsDisabled(true);
        setProgress(0, "正在建立匯入任務", "已送出 PDF 匯入請求，正在建立後台任務。");

        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {
              "x-learning-supervisor-import": "async",
              Accept: "application/json",
            },
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.detail || "匯入請求失敗。");
          }
          await pollJob(payload.job_id);
        } catch (error) {
          setControlsDisabled(false);
          setSubmittingState(true);
          if (statusDetail) {
            statusDetail.textContent = error instanceof Error ? error.message : "匯入請求失敗。";
          }
        }
      });

      if (activeJobId) {
        setProgress(0, "正在恢復匯入任務", "這份 PDF 仍在背景處理中，正在同步目前狀態。");
        void pollJob(activeJobId);
      }
    });
  }

  function queueMathTypeset(targets) {
    if (!mathEnabled) {
      return;
    }

    let attempts = 0;
    const typesetTargets = targets || [document.body];
    const timer = window.setInterval(() => {
      attempts += 1;
      if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
        window.clearInterval(timer);
        window.MathJax.typesetPromise(typesetTargets).catch(() => {});
        return;
      }
      if (attempts >= 12) {
        window.clearInterval(timer);
      }
    }, 250);
  }

  function setPageReady() {
    pageBody.classList.remove("is-booting");
    pageBody.classList.add("page-ready");
  }

  function initAmbientSketch() {
    if (!window.p5 || effectiveMotionLevel === "minimal") {
      return;
    }

    const container = document.getElementById("ambient-canvas");
    if (!container) {
      return;
    }

    const isCoarse = window.matchMedia("(pointer: coarse)").matches;
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const sceneConfig = effectiveMotionLevel === "soft"
      ? {
          anchorCount: isCoarse ? 58 : 68,
          filamentCount: isCoarse ? 188 : 228,
          dustCount: isCoarse ? 420 : 560,
          fieldRadius: isCoarse ? 148 : 172,
          pointerLinks: 1,
        }
      : {
          anchorCount: isCoarse ? 90 : 104,
          filamentCount: isCoarse ? 340 : 420,
          dustCount: isCoarse ? 760 : 980,
          fieldRadius: isCoarse ? 182 : 214,
          pointerLinks: 2,
        };

    new window.p5((p) => {
      const anchors = [];
      const filaments = [];
      const dustParticles = [];
      const pointer = {
        x: window.innerWidth * 0.72,
        y: window.innerHeight * 0.3,
        tx: window.innerWidth * 0.72,
        ty: window.innerHeight * 0.3,
        vx: 0,
        vy: 0,
        energy: 0.18,
      };
      const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
      let diagonalBasis = null;
      const orbitBandConfigs = {
        anchor: {
          ratios: [0.2, 0.32, 0.45, 0.58],
          caps: [0.18, 0.28, 0.3, 0.24],
          speeds: [2.1, 1.5, 1, 0.66],
          jitter: 0.014,
        },
        filament: {
          ratios: [0.14, 0.24, 0.34, 0.46, 0.58],
          caps: [0.12, 0.2, 0.26, 0.24, 0.18],
          speeds: [2.8, 2, 1.35, 0.94, 0.62],
          jitter: 0.016,
        },
        dust: {
          ratios: [0.11, 0.19, 0.28, 0.38, 0.48, 0.56],
          caps: [0.1, 0.14, 0.2, 0.22, 0.2, 0.14],
          speeds: [3.2, 2.35, 1.7, 1.15, 0.82, 0.56],
          jitter: 0.016,
        },
      };
      const orbitBandState = {
        anchor: [],
        filament: [],
        dust: [],
      };

      const refreshDiagonalBasis = () => {
        const length = Math.hypot(p.width, p.height) || 1;
        const flowX = p.width / length;
        const flowY = p.height / length;
        diagonalBasis = {
          flowX,
          flowY,
          normalX: -flowY,
          normalY: flowX,
        };
      };

      const getOrbitBandTotal = (layer) => ({
        anchor: sceneConfig.anchorCount,
        filament: sceneConfig.filamentCount,
        dust: sceneConfig.dustCount,
      })[layer];

      const resetOrbitBandState = () => {
        Object.keys(orbitBandConfigs).forEach((layer) => {
          orbitBandState[layer] = orbitBandConfigs[layer].ratios.map(() => 0);
        });
      };

      const getOrbitBandLimit = (layer, index) => {
        const config = orbitBandConfigs[layer];
        return Math.max(1, Math.round(getOrbitBandTotal(layer) * config.caps[index]));
      };

      const assignOrbitBand = (layer) => {
        const counts = orbitBandState[layer];
        let selectedIndex = 0;
        let bestFill = Infinity;

        counts.forEach((count, index) => {
          const limit = getOrbitBandLimit(layer, index);
          const fill = count / limit;
          if (fill < bestFill - 0.0001) {
            bestFill = fill;
            selectedIndex = index;
            return;
          }
          if (Math.abs(fill - bestFill) < 0.0001 && count < counts[selectedIndex]) {
            selectedIndex = index;
          }
        });

        counts[selectedIndex] += 1;
        return selectedIndex;
      };

      const buildOrbitProfile = (layer) => {
        const config = orbitBandConfigs[layer];
        const bandIndex = assignOrbitBand(layer);
        const radiusRatio =
          config.ratios[bandIndex] + p.random(-config.jitter, config.jitter);
        return {
          bandIndex,
          radius: sceneConfig.fieldRadius * radiusRatio,
          speedScale: config.speeds[bandIndex],
        };
      };

      const getAmbientSpawnPoint = (initial = false) => {
        const padding = initial ? 140 : 180;
        return {
          x: p.random(-padding * 0.42, p.width + padding * 0.12),
          y: p.random(-padding * 0.42, p.height + padding * 0.12),
        };
      };

      const constrainForwardMotion = (
        entity,
        minForwardSpeed,
        maxLateralSpeed,
        reverseLimit = 0,
        orbitThreshold = 0.34,
      ) => {
        const forwardSpeed =
          entity.vx * diagonalBasis.flowX + entity.vy * diagonalBasis.flowY;
        const lateralSpeed =
          entity.vx * diagonalBasis.normalX + entity.vy * diagonalBasis.normalY;
        const lowerBound =
          entity.capture > orbitThreshold ? -Math.abs(reverseLimit) : minForwardSpeed;
        const safeForwardSpeed = Math.max(lowerBound, forwardSpeed);
        const safeLateralSpeed = clamp(lateralSpeed, -maxLateralSpeed, maxLateralSpeed);
        entity.vx =
          diagonalBasis.flowX * safeForwardSpeed +
          diagonalBasis.normalX * safeLateralSpeed;
        entity.vy =
          diagonalBasis.flowY * safeForwardSpeed +
          diagonalBasis.normalY * safeLateralSpeed;
      };

      const applyOrbitalField = (entity, options) => {
        const fieldRadius = sceneConfig.fieldRadius * options.fieldScale;
        const offsetX = entity.x - pointer.x;
        const offsetY = entity.y - pointer.y;
        const distance = Math.hypot(offsetX, offsetY) + 0.0001;
        const influence = clamp(1 - distance / fieldRadius, 0, 1);
        const minRadius = options.minRadius;
        const maxRadius = options.maxRadius;
        const entryRadius = clamp(distance, minRadius, maxRadius);
        const preferredRadiusBase = entity.orbitRadius || entryRadius;
        const radiusNoise =
          (p.noise(entity.seed * 0.81, p.frameCount * options.radiusNoiseSpeed + entity.depth) - 0.5) * 2;
        const preferredRadius = clamp(
          preferredRadiusBase + radiusNoise * options.radiusNoiseAmount,
          minRadius,
          maxRadius,
        );
        const enteringField = influence > 0.02 && entity.capture < 0.04 && entity.orbitHold < 0.04;
        const withinRecoveryBand = distance < fieldRadius * options.holdRadiusMultiplier;
        const beyondReleaseBand = distance > fieldRadius * options.releaseRadiusMultiplier;

        if (enteringField) {
          entity.orbitLockRadius = clamp(
            preferredRadius * 0.9 + entryRadius * 0.1,
            minRadius,
            maxRadius,
          );
        } else if (!entity.orbitLockRadius) {
          entity.orbitLockRadius = preferredRadius;
        }

        if (influence > 0.01) {
          const radiusPull = entity.orbitHold > 0.12 ? options.radiusFollow : options.radiusCatch;
          const targetRadius = clamp(
            preferredRadius + (entryRadius - preferredRadius) * options.radiusDrift,
            minRadius,
            maxRadius,
          );
          entity.orbitLockRadius = clamp(
            entity.orbitLockRadius + (targetRadius - entity.orbitLockRadius) * radiusPull,
            minRadius,
            maxRadius,
          );
        } else if (entity.orbitHold < 0.02 && entity.capture < 0.02) {
          entity.orbitLockRadius = preferredRadius;
        }

        const relaxedCaptureDecay = withinRecoveryBand ? options.idleCaptureDecay : options.releaseCaptureDecay;
        const relaxedHoldDecay = withinRecoveryBand ? options.idleHoldDecay : options.releaseHoldDecay;

        entity.capture = clamp(
          Math.max(entity.capture * (influence > 0.01 ? options.captureDecay : relaxedCaptureDecay), influence * 0.998),
          0,
          1,
        );
        entity.orbitHold = clamp(
          Math.max(
            entity.orbitHold * (influence > 0.01 ? options.holdDecay : relaxedHoldDecay),
            influence * 0.998,
            entity.capture * options.holdLift,
          ),
          0,
          1,
        );

        if (beyondReleaseBand && influence < 0.01) {
          entity.capture *= options.releaseSnap;
          entity.orbitHold *= options.releaseSnap;
          if (entity.capture < 0.01 && entity.orbitHold < 0.01) {
            entity.orbitLockRadius = preferredRadius;
          }
        }

        let orbitMix = influence;
        if (withinRecoveryBand) {
          orbitMix = clamp(Math.max(influence, entity.orbitHold * options.holdWeight), 0, 1);
        }
        if (influence > 0.02) {
          orbitMix = Math.max(options.minOrbitMix, orbitMix);
        }
        const outwardX = offsetX / distance;
        const outwardY = offsetY / distance;
        const tangentX = -outwardY * entity.orbitDirection;
        const tangentY = outwardX * entity.orbitDirection;
        const radialProgress = clamp(
          (entity.orbitLockRadius - minRadius) / Math.max(1, maxRadius - minRadius),
          0,
          1,
        );
        const innerBias = 1 - radialProgress;
        const radiusBias = Math.pow(innerBias, options.radiusAngularPower);
        const angularVelocity =
          (
            options.angularBase +
            radiusBias * options.radiusAngularBoost +
            innerBias * options.innerOrbitBoost +
            Math.pow(influence, options.angularPower) * options.angularBoost +
            pointer.energy * options.energyBoost
          ) *
          (entity.orbitBandSpeed || 1) /
          Math.pow(
            Math.max(entity.orbitLockRadius, minRadius) / minRadius,
            options.angularRadiusFalloff,
          );
        const orbitSpeedRadius = Math.max(
          minRadius * 0.82,
          entity.orbitLockRadius * options.lockRadiusWeight + distance * (1 - options.lockRadiusWeight),
        );
        const outerDrag = 1 - radialProgress * options.outerAngularDrag;
        const tangentialSpeed =
          angularVelocity *
          orbitSpeedRadius *
          Math.max(0.22, outerDrag);
        const radialError = distance - entity.orbitLockRadius;
        const radialSpeed = clamp(
          -radialError * options.radialSpring * (1 + orbitMix * 0.58),
          -options.maxRadialSpeed,
          options.maxRadialSpeed,
        );

        return {
          influence,
          orbitMix,
          targetVx:
            tangentX * tangentialSpeed +
            outwardX * radialSpeed +
            pointer.vx * options.pointerLead * orbitMix,
          targetVy:
            tangentY * tangentialSpeed +
            outwardY * radialSpeed +
            pointer.vy * options.pointerLead * orbitMix,
        };
      };

      const shouldRecycleEntity = (entity) => {
        const margin = 180;
        const outsideViewport =
          entity.x < -margin ||
          entity.x > p.width + margin ||
          entity.y < -margin ||
          entity.y > p.height + margin;
        if (!outsideViewport) {
          return false;
        }

        const pointerDistance = Math.hypot(pointer.x - entity.x, pointer.y - entity.y);
        return pointerDistance > sceneConfig.fieldRadius * 1.36;
      };

      class Anchor {
        constructor() {
          this.seed = p.random(1000);
          this.depth = p.random(0.74, 1.26);
          this.size = p.random(3.8, 6.8);
          this.baseSpeed = p.random(0.34, 0.62) * this.depth;
          const orbitProfile = buildOrbitProfile("anchor");
          this.orbitBandIndex = orbitProfile.bandIndex;
          this.orbitBandSpeed = orbitProfile.speedScale;
          this.orbitRadius = orbitProfile.radius;
          this.vx = 0;
          this.vy = 0;
          this.x = 0;
          this.y = 0;
          this.glow = 0;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
          this.orbitDirection = p.random() > 0.5 ? 1 : -1;
          this.reset(true);
        }

        reset(initial = false) {
          const point = getAmbientSpawnPoint(initial);
          this.x = point.x;
          this.y = point.y;
          this.vx = diagonalBasis.flowX * this.baseSpeed;
          this.vy = diagonalBasis.flowY * this.baseSpeed;
          this.glow = 0.22;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
        }

        update() {
          const time = p.frameCount * 0.0042;
          const turbulence =
            (p.noise(
              this.seed + this.x * 0.0009,
              this.y * 0.0011,
              time * (0.92 + this.depth * 0.16),
            ) - 0.5) *
            (0.34 + this.depth * 0.12);
          const targetVx =
            diagonalBasis.flowX * this.baseSpeed +
            diagonalBasis.normalX * turbulence;
          const targetVy =
            diagonalBasis.flowY * this.baseSpeed +
            diagonalBasis.normalY * turbulence;
          const orbitalField = applyOrbitalField(this, {
            fieldScale: 1.04,
            minRadius: 26,
            maxRadius: sceneConfig.fieldRadius * 0.62,
            radiusCatch: 0.2,
            radiusFollow: 0.04,
            radiusDrift: 0.05,
            radiusNoiseSpeed: 0.0021,
            radiusNoiseAmount: 4,
            lockRadiusWeight: 0.84,
            angularRadiusFalloff: 1.08,
            captureDecay: 0.995,
            idleCaptureDecay: 0.986,
            releaseCaptureDecay: 0.84,
            holdDecay: 0.9993,
            idleHoldDecay: 0.982,
            releaseHoldDecay: 0.78,
            holdLift: 0.985,
            holdWeight: 0.992,
            minOrbitMix: 0.62,
            angularBase: 0.028,
            angularBoost: 0.2,
            angularPower: 2.18,
            innerOrbitBoost: 0.22,
            radiusAngularBoost: 0.2,
            radiusAngularPower: 1.45,
            outerAngularDrag: 0.26,
            energyBoost: 0.032,
            radialSpring: 0.088,
            maxRadialSpeed: 4.8,
            pointerLead: 0.16,
            holdRadiusMultiplier: 1.06,
            releaseRadiusMultiplier: 1.16,
            releaseSnap: 0.58,
          });
          const settle = 1 - orbitalField.orbitMix * 0.985;
          const blendedVx = targetVx * (1 - orbitalField.orbitMix) + orbitalField.targetVx * orbitalField.orbitMix;
          const blendedVy = targetVy * (1 - orbitalField.orbitMix) + orbitalField.targetVy * orbitalField.orbitMix;
          this.vx += (blendedVx - this.vx) * (0.026 * settle + 0.08 + orbitalField.orbitMix * 0.09);
          this.vy += (blendedVy - this.vy) * (0.026 * settle + 0.08 + orbitalField.orbitMix * 0.09);

          if (orbitalField.orbitMix < 0.12) {
            constrainForwardMotion(
              this,
              this.baseSpeed * 0.48,
              1.16 + this.depth * 0.24,
            );
          }
          this.x += this.vx;
          this.y += this.vy;

          if (shouldRecycleEntity(this)) {
            this.reset();
          }

          this.glow =
            0.22 +
            orbitalField.influence * 0.48 +
            orbitalField.orbitMix * 0.42 +
            pointer.energy * 0.14;
        }

        draw() {
          p.noStroke();
          p.fill(188, 68, 100, 12 + this.glow * 8);
          p.circle(this.x, this.y, this.size * 3.2);
          p.fill(34, 62, 100, 10 + this.glow * 4);
          p.circle(this.x, this.y, this.size * 1.8);
          p.fill(190, 30, 100, 58 + this.glow * 14);
          p.circle(this.x, this.y, this.size);
        }
      }

      class DustParticle {
        constructor() {
          this.seed = p.random(1000);
          this.depth = p.random(0.64, 1.28);
          this.size = p.random(0.7, 1.9);
          this.hue = p.random([168, 176, 184, 192, 198]);
          this.baseSpeed = p.random(0.62, 1.18) * this.depth;
          this.tailLength = p.random(4, 9);
          const orbitProfile = buildOrbitProfile("dust");
          this.orbitBandIndex = orbitProfile.bandIndex;
          this.orbitBandSpeed = orbitProfile.speedScale;
          this.orbitRadius = orbitProfile.radius;
          this.vx = 0;
          this.vy = 0;
          this.x = 0;
          this.y = 0;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
          this.orbitDirection = p.random() > 0.5 ? 1 : -1;
          this.reset(true);
        }

        reset(initial = false) {
          const point = getAmbientSpawnPoint(initial);
          this.x = point.x;
          this.y = point.y;
          const speed = this.baseSpeed * p.random(0.9, 1.24);
          this.vx = diagonalBasis.flowX * speed;
          this.vy = diagonalBasis.flowY * speed;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
        }

        update() {
          const time = p.frameCount * 0.0068;
          const turbulence =
            (p.noise(
              this.seed + this.x * 0.0012,
              this.y * 0.0012,
              time * (0.92 + this.depth * 0.18),
            ) - 0.5) *
            (0.28 + this.depth * 0.12);
          const targetVx = diagonalBasis.flowX * this.baseSpeed + diagonalBasis.normalX * turbulence;
          const targetVy = diagonalBasis.flowY * this.baseSpeed + diagonalBasis.normalY * turbulence;
          const orbitalField = applyOrbitalField(this, {
            fieldScale: 0.98,
            minRadius: 16,
            maxRadius: sceneConfig.fieldRadius * 0.58,
            radiusCatch: 0.22,
            radiusFollow: 0.05,
            radiusDrift: 0.04,
            radiusNoiseSpeed: 0.0028,
            radiusNoiseAmount: 5,
            lockRadiusWeight: 0.88,
            angularRadiusFalloff: 1.34,
            captureDecay: 0.996,
            idleCaptureDecay: 0.985,
            releaseCaptureDecay: 0.82,
            holdDecay: 0.99935,
            idleHoldDecay: 0.981,
            releaseHoldDecay: 0.76,
            holdLift: 0.988,
            holdWeight: 0.994,
            minOrbitMix: 0.7,
            angularBase: 0.034,
            angularBoost: 0.28,
            angularPower: 2.45,
            innerOrbitBoost: 0.44,
            radiusAngularBoost: 0.42,
            radiusAngularPower: 1.72,
            outerAngularDrag: 0.34,
            energyBoost: 0.03,
            radialSpring: 0.11,
            maxRadialSpeed: 4.2,
            pointerLead: 0.13,
            holdRadiusMultiplier: 1.04,
            releaseRadiusMultiplier: 1.12,
            releaseSnap: 0.54,
          });
          const settle = 1 - orbitalField.orbitMix * 0.988;
          const blendedVx = targetVx * (1 - orbitalField.orbitMix) + orbitalField.targetVx * orbitalField.orbitMix;
          const blendedVy = targetVy * (1 - orbitalField.orbitMix) + orbitalField.targetVy * orbitalField.orbitMix;
          this.vx += (blendedVx - this.vx) * (0.022 * settle + 0.09 + orbitalField.orbitMix * 0.1);
          this.vy += (blendedVy - this.vy) * (0.022 * settle + 0.09 + orbitalField.orbitMix * 0.1);

          if (orbitalField.orbitMix < 0.12) {
            constrainForwardMotion(
              this,
              this.baseSpeed * 0.3,
              1.48 + this.depth * 0.24,
            );
          }
          this.x += this.vx;
          this.y += this.vy;

          if (shouldRecycleEntity(this)) {
            this.reset();
          }
        }

        drawMotion() {
          const speed = Math.hypot(this.vx, this.vy);
          const normalizedSpeed = speed > 0.0001 ? 1 / speed : 0;
          const tailLength = Math.min(this.tailLength, 3.8 + speed * 2.2);
          const tailX = this.x - this.vx * normalizedSpeed * tailLength;
          const tailY = this.y - this.vy * normalizedSpeed * tailLength;
          const fieldInfluence =
            clamp(1 - Math.hypot(pointer.x - this.x, pointer.y - this.y) / (sceneConfig.fieldRadius * 1.08), 0, 1);
          const alpha = clamp(1.8 + this.depth * 2.2 + fieldInfluence * 4.2, 1.8, 8);
          p.stroke(this.hue, 30, 100, alpha);
          p.strokeWeight(0.32 + this.depth * 0.16);
          p.line(tailX, tailY, this.x, this.y);
        }

        drawCore() {
          const fieldInfluence =
            clamp(1 - Math.hypot(pointer.x - this.x, pointer.y - this.y) / (sceneConfig.fieldRadius * 0.92), 0, 1);
          const alpha = 4 + this.depth * 3.6 + fieldInfluence * 6;
          p.noStroke();
          p.fill(this.hue, 20 + fieldInfluence * 10, 100, alpha);
          p.circle(this.x, this.y, this.size + fieldInfluence * 0.22);
        }
      }

      class Filament {
        constructor() {
          this.seed = p.random(1000);
          this.depth = p.random(0.68, 1.44);
          this.strokeWidth = p.random(0.5, 1.1);
          this.size = p.random(1.4, 4.2);
          this.hue = p.random([168, 184, 192, 198]);
          this.baseSpeed = p.random(0.82, 1.45) * this.depth;
          this.tailLength = p.random(10, 22);
          const orbitProfile = buildOrbitProfile("filament");
          this.orbitBandIndex = orbitProfile.bandIndex;
          this.orbitBandSpeed = orbitProfile.speedScale;
          this.orbitRadius = orbitProfile.radius;
          this.vx = 0;
          this.vy = 0;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
          this.orbitDirection = p.random() > 0.5 ? 1 : -1;
          this.reset(true);
        }

        reset(initial = false) {
          const point = getAmbientSpawnPoint(initial);
          this.x = point.x;
          this.y = point.y;
          this.px = this.x;
          this.py = this.y;
          const speed = this.baseSpeed * p.random(0.86, 1.18);
          this.vx = diagonalBasis.flowX * speed;
          this.vy = diagonalBasis.flowY * speed;
          this.capture = 0;
          this.orbitHold = 0;
          this.orbitLockRadius = 0;
        }

        update() {
          this.px = this.x;
          this.py = this.y;

          const time = p.frameCount * 0.006;
          const turbulence =
            (p.noise(
              this.seed + this.x * 0.0011,
              this.y * 0.0013,
              time * (0.86 + this.depth * 0.2),
            ) - 0.5) *
            (0.48 + this.depth * 0.2);
          const targetVx = diagonalBasis.flowX * this.baseSpeed + diagonalBasis.normalX * turbulence;
          const targetVy = diagonalBasis.flowY * this.baseSpeed + diagonalBasis.normalY * turbulence;
          const orbitalField = applyOrbitalField(this, {
            fieldScale: 0.94,
            minRadius: 18,
            maxRadius: sceneConfig.fieldRadius * 0.6,
            radiusCatch: 0.2,
            radiusFollow: 0.042,
            radiusDrift: 0.045,
            radiusNoiseSpeed: 0.0024,
            radiusNoiseAmount: 5,
            lockRadiusWeight: 0.86,
            angularRadiusFalloff: 1.22,
            captureDecay: 0.9964,
            idleCaptureDecay: 0.986,
            releaseCaptureDecay: 0.83,
            holdDecay: 0.99945,
            idleHoldDecay: 0.982,
            releaseHoldDecay: 0.77,
            holdLift: 0.99,
            holdWeight: 0.995,
            minOrbitMix: 0.66,
            angularBase: 0.031,
            angularBoost: 0.24,
            angularPower: 2.3,
            innerOrbitBoost: 0.34,
            radiusAngularBoost: 0.3,
            radiusAngularPower: 1.58,
            outerAngularDrag: 0.3,
            energyBoost: 0.032,
            radialSpring: 0.1,
            maxRadialSpeed: 4.6,
            pointerLead: 0.15,
            holdRadiusMultiplier: 1.05,
            releaseRadiusMultiplier: 1.14,
            releaseSnap: 0.56,
          });
          const settle = 1 - orbitalField.orbitMix * 0.989;
          const blendedVx = targetVx * (1 - orbitalField.orbitMix) + orbitalField.targetVx * orbitalField.orbitMix;
          const blendedVy = targetVy * (1 - orbitalField.orbitMix) + orbitalField.targetVy * orbitalField.orbitMix;
          this.vx += (blendedVx - this.vx) * (0.02 * settle + 0.086 + orbitalField.orbitMix * 0.1);
          this.vy += (blendedVy - this.vy) * (0.02 * settle + 0.086 + orbitalField.orbitMix * 0.1);

          if (orbitalField.orbitMix < 0.14) {
            constrainForwardMotion(
              this,
              this.baseSpeed * 0.18,
              2.08 + this.depth * 0.36,
            );
          }
          this.x += this.vx;
          this.y += this.vy;

          if (shouldRecycleEntity(this)) {
            this.reset();
          }
        }

        drawMotion() {
          const speed = Math.hypot(this.vx, this.vy);
          const normalizedSpeed = speed > 0.0001 ? 1 / speed : 0;
          const tailLength = Math.min(this.tailLength, 8 + speed * 5.2);
          const tailX = this.x - this.vx * normalizedSpeed * tailLength;
          const tailY = this.y - this.vy * normalizedSpeed * tailLength;
          const fieldInfluence = clamp(1 - Math.hypot(pointer.x - this.x, pointer.y - this.y) / (sceneConfig.fieldRadius * 1.05), 0, 1);
          const alpha = clamp(6 + this.depth * 5 + fieldInfluence * 12, 6, 22);
          p.stroke(this.hue, 62, 100, alpha);
          p.strokeWeight(this.strokeWidth * (0.72 + this.depth * 0.14));
          p.line(tailX, tailY, this.x, this.y);
        }

        drawCore() {
          const fieldInfluence = clamp(1 - Math.hypot(pointer.x - this.x, pointer.y - this.y) / (sceneConfig.fieldRadius * 0.96), 0, 1);
          const alpha = 12 + this.depth * 14 + fieldInfluence * 18;
          p.noStroke();
          p.fill(this.hue, 42, 100, alpha * 0.16);
          p.circle(this.x, this.y, this.size * (2.1 + fieldInfluence * 0.42));
          p.fill(this.hue, 18 + fieldInfluence * 16, 100, alpha);
          p.circle(this.x, this.y, this.size + fieldInfluence * 0.42);
        }
      }

      const seedScene = () => {
        anchors.length = 0;
        filaments.length = 0;
        dustParticles.length = 0;
        resetOrbitBandState();

        for (let index = 0; index < sceneConfig.anchorCount; index += 1) {
          anchors.push(new Anchor());
        }

        for (let index = 0; index < sceneConfig.filamentCount; index += 1) {
          filaments.push(new Filament());
        }

        for (let index = 0; index < sceneConfig.dustCount; index += 1) {
          dustParticles.push(new DustParticle());
        }
      };

      const updatePointer = () => {
        if (!finePointer) {
          pointer.tx = p.width * 0.54 + Math.cos(p.frameCount * 0.012) * p.width * 0.14;
          pointer.ty = p.height * 0.34 + Math.sin(p.frameCount * 0.009) * p.height * 0.11;
        }

        const dx = pointer.tx - pointer.x;
        const dy = pointer.ty - pointer.y;
        pointer.vx = dx;
        pointer.vy = dy;
        pointer.x += dx * (finePointer ? 0.15 : 0.08);
        pointer.y += dy * (finePointer ? 0.15 : 0.08);
        pointer.energy = clamp(
          pointer.energy * 0.86 + Math.min(1, Math.hypot(dx, dy) / 46) * 0.2,
          0.12,
          0.98,
        );
      };

      const renderAtmosphere = () => {
        p.push();
        p.blendMode(p.ADD);
        p.noStroke();
        const pulse = Math.sin(p.frameCount * 0.045) * 0.5 + 0.5;
        const outerSize = 190 + pointer.energy * 110 + pulse * 14;
        const midSize = 116 + pointer.energy * 68;
        const innerSize = 36 + pointer.energy * 20;
        p.fill(188, 42, 16, 3.6 + pointer.energy * 2.4);
        p.circle(pointer.x, pointer.y, outerSize);
        p.fill(196, 50, 18, 5 + pointer.energy * 3.2);
        p.circle(pointer.x, pointer.y, midSize);
        p.fill(34, 34, 100, 9 + pointer.energy * 8);
        p.circle(pointer.x, pointer.y, innerSize);

        p.noFill();
        p.stroke(188, 40, 100, 4 + pointer.energy * 4);
        p.strokeWeight(1.1);
        p.circle(pointer.x, pointer.y, 84 + pointer.energy * 30 + pulse * 10);
        p.stroke(34, 24, 100, 2.4 + pointer.energy * 3.2);
        p.strokeWeight(0.8);
        p.circle(pointer.x, pointer.y, 128 + pointer.energy * 44 - pulse * 8);
        p.pop();

        p.noStroke();
        p.fill(188, 28, 8, 2.2);
        p.circle(p.width * 0.82, p.height * 0.7, 220);
      };

      const renderAnchorConnections = () => {
        p.push();
        p.blendMode(p.ADD);
        p.strokeWeight(1);

        for (let i = 0; i < anchors.length; i += 1) {
          const a = anchors[i];
          for (let j = i + 1; j < anchors.length; j += 1) {
            const b = anchors[j];
            const distance = Math.hypot(a.x - b.x, a.y - b.y);
            if (distance < 168) {
              const alpha = p.map(distance, 0, 168, 9.4, 0) * (0.38 + pointer.energy * 0.16);
              p.stroke(192, 58, 100, alpha);
              p.line(a.x, a.y, b.x, b.y);
            }
          }
        }

        const linkedAnchors = anchors
          .map((anchor) => ({
            anchor,
            distance: Math.hypot(pointer.x - anchor.x, pointer.y - anchor.y),
          }))
          .filter((entry) => entry.distance < sceneConfig.fieldRadius + 10)
          .sort((left, right) => left.distance - right.distance)
          .slice(0, pointer.energy > 0.58 ? sceneConfig.pointerLinks : 1);

        for (const entry of linkedAnchors) {
          const alpha =
            p.map(entry.distance, 0, sceneConfig.fieldRadius + 24, 14, 2) *
            (0.62 + pointer.energy * 0.22);
          p.stroke(34, 44, 100, alpha);
          p.line(pointer.x, pointer.y, entry.anchor.x, entry.anchor.y);
        }

        p.pop();
      };

      const renderPointerField = () => {
        p.push();
        p.blendMode(p.ADD);
        const context = p.drawingContext;
        context.save();
        context.shadowBlur = 24 + pointer.energy * 38;
        context.shadowColor = `rgba(117, 247, 227, ${0.14 + pointer.energy * 0.18})`;
        p.noStroke();
        p.fill(34, 34, 100, 8 + pointer.energy * 7);
        p.circle(pointer.x, pointer.y, 16 + pointer.energy * 14);
        context.restore();

        const ripple = Math.sin(p.frameCount * 0.07) * 0.5 + 0.5;
        p.noFill();
        p.stroke(188, 34, 100, 4 + pointer.energy * 4);
        p.strokeWeight(0.9);
        p.circle(pointer.x, pointer.y, 56 + pointer.energy * 18 + ripple * 8);
        p.stroke(34, 28, 100, 3 + pointer.energy * 3);
        p.strokeWeight(0.7);
        p.circle(pointer.x, pointer.y, sceneConfig.fieldRadius * 0.72 + ripple * 8);
        p.pop();
      };

      const handlePointerMove = (event) => {
        pointer.tx = event.clientX;
        pointer.ty = event.clientY;
      };

      p.setup = () => {
        const canvas = p.createCanvas(window.innerWidth, window.innerHeight);
        canvas.parent(container);
        canvas.style("pointer-events", "none");
        canvas.style("mix-blend-mode", "screen");
        canvas.style("opacity", "0.95");
        p.pixelDensity(1);
        p.colorMode(p.HSB, 360, 100, 100, 100);
        p.frameRate(36);
        refreshDiagonalBasis();
        seedScene();
        window.addEventListener("mousemove", handlePointerMove, { passive: true });
      };

      p.draw = () => {
        p.clear();
        updatePointer();

        for (const anchor of anchors) {
          anchor.update();
        }

        p.push();
        p.blendMode(p.ADD);
        for (const dustParticle of dustParticles) {
          dustParticle.update();
          dustParticle.drawMotion();
        }
        p.pop();

        p.push();
        p.blendMode(p.ADD);
        for (const filament of filaments) {
          filament.update();
          filament.drawMotion();
        }
        p.pop();

        renderAtmosphere();
        renderAnchorConnections();

        for (const anchor of anchors) {
          anchor.draw();
        }

        dustParticles.forEach((dustParticle) => {
          dustParticle.drawCore();
        });

        filaments.forEach((filament) => {
          filament.drawCore();
        });

        renderPointerField();
      };

      p.windowResized = () => {
        p.resizeCanvas(window.innerWidth, window.innerHeight);
        pointer.tx = Math.min(pointer.tx, window.innerWidth);
        pointer.ty = Math.min(pointer.ty, window.innerHeight);
        refreshDiagonalBasis();
        seedScene();
      };
    });
  }

  function rebindImportSubmitLoaders() {
    const importJobStorageKey = "ls-active-import-job-id";

    document.querySelectorAll("form[data-loading-submit]").forEach((originalForm) => {
      if (!originalForm.querySelector("[data-import-status-label]")) {
        return;
      }

      const form = originalForm.cloneNode(true);
      originalForm.replaceWith(form);

      const overlay = form.querySelector("[data-submit-loader]");
      const submitControls = Array.from(form.querySelectorAll("button[type='submit'], input[type='submit']"));
      const fallbackText = form.dataset.loadingText || "正在處理，請稍候...";
      const statusLabel = form.querySelector("[data-import-status-label]");
      const statusDetail = form.querySelector("[data-import-status-detail]");
      const statusHelp = form.querySelector("[data-import-status-help]");
      const dismissButton = form.querySelector("[data-import-status-dismiss]");
      const progressFill = form.querySelector("[data-import-progress-fill]");
      const progressText = form.querySelector("[data-import-progress-text]");
      const urlJobId = new URL(window.location.href).searchParams.get("job") || "";
      let storedJobId = "";
      try {
        storedJobId = window.sessionStorage.getItem(importJobStorageKey) || "";
      } catch (_error) {}
      const activeJobId = urlJobId || form.dataset.activeImportJobId || storedJobId || "";
      let pollHandle = 0;
      let consecutivePollFailures = 0;
      const maxTransientPollFailures = 6;

      const setSubmittingState = (isSubmitting, options = {}) => {
        const keepVisible = Boolean(options.keepVisible);
        form.classList.toggle("is-submitting", isSubmitting);
        if (overlay) {
          overlay.hidden = !isSubmitting && !keepVisible;
        }
      };

      const setDismissVisible = (visible) => {
        if (dismissButton instanceof HTMLElement) {
          dismissButton.hidden = !visible;
        }
      };

      const setHelpText = (text) => {
        if (statusHelp && text) {
          statusHelp.textContent = text;
        }
      };

      const setProgress = (percent, label, detail) => {
        const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
        if (progressFill) {
          progressFill.style.width = `${safePercent}%`;
        }
        if (progressText) {
          progressText.textContent = `${Math.round(safePercent)}%`;
        }
        if (statusLabel && label) {
          statusLabel.textContent = label;
        }
        if (statusDetail && detail) {
          statusDetail.textContent = detail;
        }
      };

      const setControlsDisabled = (disabled) => {
        submitControls.forEach((control) => {
          const loadingText = control.dataset.loadingText || fallbackText;
          control.disabled = disabled;
          control.setAttribute("aria-busy", disabled ? "true" : "false");

          if (control instanceof HTMLInputElement) {
            control.value = disabled
              ? loadingText
              : (control.dataset.originalValue || control.defaultValue || control.value);
            return;
          }

          if (!control.dataset.originalText) {
            control.dataset.originalText = control.textContent || "";
          }
          control.textContent = disabled ? loadingText : control.dataset.originalText;
        });
      };

      const stopPolling = () => {
        if (pollHandle) {
          window.clearTimeout(pollHandle);
          pollHandle = 0;
        }
      };

      const persistActiveJobId = (jobId) => {
        try {
          if (jobId) {
            window.sessionStorage.setItem(importJobStorageKey, jobId);
          } else {
            window.sessionStorage.removeItem(importJobStorageKey);
          }
        } catch (_error) {}
      };

      const setActiveJobInUrl = (jobId) => {
        const nextUrl = new URL(window.location.href);
        if (jobId) {
          nextUrl.searchParams.set("job", jobId);
        } else {
          nextUrl.searchParams.delete("job");
        }
        window.history.replaceState({}, "", nextUrl.toString());
        persistActiveJobId(jobId);
      };

      const finishPollingWithMessage = (message, options = {}) => {
        const keepVisible = Boolean(options.keepVisible);
        stopPolling();
        setControlsDisabled(false);
        setSubmittingState(false, { keepVisible });
        setDismissVisible(keepVisible);
        if (statusDetail) {
          statusDetail.textContent = message;
        }
      };

      const pollJob = async (jobId) => {
        stopPolling();
        setSubmittingState(true);
        setControlsDisabled(true);
        setDismissVisible(false);

        try {
          const response = await fetch(`/imports/${encodeURIComponent(jobId)}`, {
            headers: {
              Accept: "application/json",
            },
            cache: "no-store",
          });
          if (!response.ok) {
            throw new Error("無法取得匯入狀態。");
          }

          const job = await response.json();
          consecutivePollFailures = 0;
          setProgress(job.progress_percent, job.status_label, job.detail || job.error_message || "");

          if (job.status === "completed" && job.resource_id) {
            setActiveJobInUrl("");
            window.location.href = `/resources/${encodeURIComponent(job.resource_id)}`;
            return;
          }

          if (job.status === "failed") {
            setActiveJobInUrl(jobId);
            setHelpText("匯入已停止。你可以直接在這裡看到錯誤，再決定是否重新提交。");
            finishPollingWithMessage(job.error_message || job.detail || "匯入失敗。", { keepVisible: true });
            return;
          }

          setHelpText(
            job.status === "queued"
              ? "任務已建立，正在等待背景程序接手。"
              : "目前仍在背景解析中。即使切換到別的頁面，再回來也會自動恢復這個狀態。",
          );

          pollHandle = window.setTimeout(() => {
            void pollJob(jobId);
          }, 1200);
        } catch (error) {
          consecutivePollFailures += 1;
          const retryMessage = consecutivePollFailures >= maxTransientPollFailures
            ? "匯入狀態同步暫時失敗。請稍後重新整理頁面；如果背景任務仍存在，頁面會再次接上。"
            : "和本地服務的連線短暫中斷，正在自動重試匯入狀態。";
          if (statusDetail) {
            statusDetail.textContent = retryMessage;
          }
          setHelpText("如果你只是中途切到別的頁面，這裡仍會持續自動重試。");
          if (consecutivePollFailures >= maxTransientPollFailures) {
            finishPollingWithMessage(
              error instanceof Error ? `${retryMessage} ${error.message}` : retryMessage,
              { keepVisible: true },
            );
            return;
          }
          pollHandle = window.setTimeout(() => {
            void pollJob(jobId);
          }, Math.min(5000, 1200 * consecutivePollFailures));
        }
      };

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setSubmittingState(true);
        setControlsDisabled(true);
        setDismissVisible(false);
        consecutivePollFailures = 0;
        setHelpText("任務建立後會在背景持續解析；切換頁面再回來，也會自動恢復進度。");
        setProgress(0, "正在建立匯入任務", "已送出 PDF 匯入請求，正在建立背景任務。");

        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {
              "x-learning-supervisor-import": "async",
              Accept: "application/json",
            },
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.detail || "匯入請求失敗。");
          }
          setActiveJobInUrl(payload.job_id);
          await pollJob(payload.job_id);
        } catch (error) {
          setControlsDisabled(false);
          setSubmittingState(false);
          if (statusDetail) {
            statusDetail.textContent = error instanceof Error ? error.message : "匯入請求失敗。";
          }
        }
      });

      dismissButton?.addEventListener("click", () => {
        setSubmittingState(false);
        setDismissVisible(false);
      });

      if (activeJobId) {
        setActiveJobInUrl(activeJobId);
        setHelpText("這份 PDF 的背景任務仍可追蹤；就算中途離開這一頁，回來也會繼續同步。");
        setProgress(0, "正在恢復匯入任務", "這份 PDF 仍在背景處理中，正在同步目前狀態。");
        void pollJob(activeJobId);
      }
    });
  }

  function initTaskTimerV3() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const taskSignature = timerRoot.dataset.taskSignature || taskId;
    const storageKey = `ls-task-timer:v3:${taskSignature}`;
    const legacyKeys = [`ls-task-timer:${taskId}`, `ls-task-timer:v2:${taskId}`, `ls-task-timer:v3:${taskId}`];
    const defaultMinutes = Math.max(1, Number(timerRoot.dataset.defaultMinutes) || 25);
    const display = timerRoot.querySelector("[data-timer-display]");
    const orb = timerRoot.querySelector("[data-timer-orb]");
    const stateBadge = timerRoot.querySelector("[data-timer-state]");
    const minutesInput = timerRoot.querySelector("[data-timer-minutes]");
    const startButton = timerRoot.querySelector("[data-timer-start]");
    const pauseButton = timerRoot.querySelector("[data-timer-pause]");
    const finishButton = timerRoot.querySelector("[data-timer-finish]");
    const alertBox = timerRoot.querySelector("[data-timer-alert]");
    const extendButtons = Array.from(timerRoot.querySelectorAll("[data-timer-extend]"));
    const completeForm = document.querySelector("[data-task-complete-form]");
    const baseTitle = document.title;
    const timerStateClassMap = {
      idle: "status-scheduled",
      running: "status-live",
      paused: "status-in_review",
      expired: "status-active",
      finished: "status-completed",
    };

    const buildIdleState = (minutes) => ({
      durationSeconds: minutes * 60,
      remainingSeconds: minutes * 60,
      endsAt: 0,
      running: false,
      paused: false,
      expired: false,
      finished: false,
      chimed: false,
    });

    const state = buildIdleState(defaultMinutes);
    let timerHandle = 0;
    let audioContext = null;

    const safeNumber = (value, fallback) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : fallback;
    };

    const clampMinutes = (value) => {
      const parsed = Math.round(safeNumber(value, defaultMinutes));
      return Math.min(240, Math.max(1, parsed));
    };

    const setBadge = (text, variant) => {
      if (!stateBadge) {
        return;
      }
      stateBadge.textContent = text;
      stateBadge.className = `status-pill ${timerStateClassMap[variant] || timerStateClassMap.idle}`;
    };

    const setTimerClasses = (variant) => {
      timerRoot.classList.toggle("is-running", variant === "running");
      timerRoot.classList.toggle("is-expired", variant === "expired");
      timerRoot.classList.toggle("is-finished", variant === "finished");
      timerRoot.classList.toggle("is-paused", variant === "paused");
    };

    const stopTicker = () => {
      if (!timerHandle) {
        return;
      }
      window.clearInterval(timerHandle);
      timerHandle = 0;
    };

    const clearState = () => {
      try {
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const saveState = () => {
      try {
        if (state.running || state.paused) {
          window.localStorage.setItem(
            storageKey,
            JSON.stringify({
              taskSignature,
              durationSeconds: state.durationSeconds,
              remainingSeconds: state.remainingSeconds,
              endsAt: state.endsAt,
              running: state.running,
              paused: state.paused,
            }),
          );
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const ensureAudioContext = () => {
      if (audioContext || !window.AudioContext) {
        return;
      }
      try {
        audioContext = new window.AudioContext();
      } catch (_error) {
        audioContext = null;
      }
    };

    const playChime = () => {
      if (!audioContext) {
        return;
      }
      const startAt = audioContext.currentTime;
      [0, 0.22].forEach((offset, index) => {
        const oscillator = audioContext.createOscillator();
        const gain = audioContext.createGain();
        oscillator.type = "sine";
        oscillator.frequency.value = index === 0 ? 880 : 1046;
        gain.gain.setValueAtTime(0.0001, startAt + offset);
        gain.gain.exponentialRampToValueAtTime(0.08, startAt + offset + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, startAt + offset + 0.16);
        oscillator.connect(gain);
        gain.connect(audioContext.destination);
        oscillator.start(startAt + offset);
        oscillator.stop(startAt + offset + 0.18);
      });
    };

    const formatClock = (totalSeconds) => {
      const safeSeconds = Math.max(0, Math.floor(totalSeconds));
      const minutes = Math.floor(safeSeconds / 60);
      const seconds = safeSeconds % 60;
      return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    };

    const applyIdleState = (minutes) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.endsAt = nextState.endsAt;
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
    };

    const ensureIdleState = () => {
      applyIdleState(clampMinutes(minutesInput ? minutesInput.value : defaultMinutes));
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      applyIdleState(minutes);
      stopTicker();
      clearState();
    };

    const expireTimer = () => {
      state.running = false;
      state.paused = false;
      state.expired = true;
      state.finished = false;
      state.remainingSeconds = 0;
      state.endsAt = 0;
      clearState();
    };

    const syncClock = () => {
      if (!state.running) {
        return;
      }
      const remainingMs = state.endsAt - Date.now();
      if (remainingMs <= 0) {
        expireTimer();
        return;
      }
      state.remainingSeconds = Math.ceil(remainingMs / 1000);
      state.expired = false;
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          ensureIdleState();
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || parsed.taskSignature !== taskSignature || (!parsed.running && !parsed.paused)) {
          clearState();
          ensureIdleState();
          return;
        }
        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.endsAt = Math.max(0, safeNumber(parsed.endsAt, 0));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.chimed = false;
        if (state.running) {
          syncClock();
        }
      } catch (_error) {
        clearState();
        ensureIdleState();
      }
    };

    const renderTimer = () => {
      syncClock();
      const progress = state.durationSeconds > 0
        ? Math.min(1, Math.max(0, 1 - state.remainingSeconds / state.durationSeconds))
        : 0;

      if (display) {
        display.textContent = formatClock(state.remainingSeconds);
      }
      if (orb) {
        orb.style.setProperty("--timer-progress", `${(progress * 100).toFixed(2)}%`);
      }

      if (state.running) {
        state.expired = false;
        setBadge("計時中", "running");
        setTimerClasses("running");
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到了", "expired");
        setTimerClasses("expired");
        document.title = `[時間到了] ${baseTitle}`;
        if (!state.chimed) {
          playChime();
          state.chimed = true;
        }
      } else if (state.finished) {
        setBadge("已提前結束", "finished");
        setTimerClasses("finished");
        document.title = baseTitle;
      } else if (state.paused) {
        setBadge("已暫停", "paused");
        setTimerClasses("paused");
        document.title = baseTitle;
      } else {
        state.expired = false;
        setBadge("未開始", "idle");
        setTimerClasses("idle");
        document.title = baseTitle;
      }

      if (minutesInput) {
        if (!state.running) {
          minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
        }
        minutesInput.disabled = state.running;
      }
      if (startButton) {
        startButton.disabled = state.running;
        startButton.textContent = state.paused || state.expired || state.finished ? "重新開始" : "開始計時";
      }
      if (pauseButton) {
        pauseButton.disabled = !state.running && !state.paused;
        pauseButton.textContent = state.paused ? "繼續" : "暫停";
      }
      if (finishButton) {
        finishButton.disabled = !state.running && !state.paused && !state.expired;
      }
      extendButtons.forEach((button) => {
        button.disabled = (!state.running && !state.paused && !state.expired) || state.finished;
      });
      if (alertBox) {
        alertBox.hidden = !state.expired;
      }

      saveState();
    };

    const startTicker = () => {
      stopTicker();
      timerHandle = window.setInterval(() => {
        renderTimer();
        if (!state.running) {
          stopTicker();
        }
      }, 200);
    };

    const applyMinutesFromInput = () => {
      resetToIdle();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      applyIdleState(minutes);
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      state.endsAt = Date.now() + state.durationSeconds * 1000;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        syncClock();
        if (state.expired) {
          renderTimer();
          return;
        }
        state.running = false;
        state.paused = true;
        state.endsAt = 0;
        stopTicker();
        renderTimer();
        return;
      }

      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.expired = false;
        state.finished = false;
        state.endsAt = Date.now() + state.remainingSeconds * 1000;
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = Math.max(60, Math.round(safeNumber(extraMinutes, 10)) * 60);
      if (state.running) {
        syncClock();
      }
      state.durationSeconds += extraSeconds;
      state.remainingSeconds = Math.max(0, state.remainingSeconds) + extraSeconds;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      ensureAudioContext();
      state.endsAt = Date.now() + state.remainingSeconds * 1000;
      startTicker();
      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.endsAt = 0;
      stopTicker();
      clearState();
      renderTimer();

      const summaryField = completeForm ? completeForm.querySelector("textarea[name='summary_text']") : null;
      if (completeForm) {
        completeForm.scrollIntoView({ behavior: effectiveMotionLevel === "minimal" ? "auto" : "smooth", block: "start" });
      }
      if (summaryField instanceof HTMLElement) {
        window.setTimeout(() => summaryField.focus(), 120);
      }
    };

    try {
      legacyKeys.forEach((key) => window.localStorage.removeItem(key));
    } catch (_error) {}

    loadState();
    if (state.running && !state.expired) {
      startTicker();
    }
    renderTimer();

    window.addEventListener("pageshow", () => {
      stopTicker();
      loadState();
      if (state.running && !state.expired) {
        startTicker();
      }
      renderTimer();
    });

    minutesInput?.addEventListener("change", applyMinutesFromInput);
    startButton?.addEventListener("click", startTimer);
    pauseButton?.addEventListener("click", togglePause);
    finishButton?.addEventListener("click", finishEarly);
    extendButtons.forEach((button) => {
      button.addEventListener("click", () => {
        extendTimer(button.dataset.timerExtend);
      });
    });

    completeForm?.addEventListener("submit", () => {
      stopTicker();
      clearState();
      document.title = baseTitle;
    });
  }

  function initPdfPreview() {
    const overlay = document.querySelector("[data-pdf-preview-overlay]");
    if (!overlay) {
      return;
    }

    const dialog = overlay.querySelector("[data-pdf-preview-dialog]");
    const documentFrame = overlay.querySelector("[data-pdf-preview-document]");
    const counter = overlay.querySelector("[data-pdf-preview-counter]");
    const prevButton = overlay.querySelector("[data-pdf-preview-prev]");
    const nextButton = overlay.querySelector("[data-pdf-preview-next]");
    const fullscreenButton = overlay.querySelector("[data-pdf-preview-fullscreen]");
    const closeButtons = Array.from(overlay.querySelectorAll("[data-pdf-preview-close]"));
    const previewItems = Array.from(document.querySelectorAll("[data-pdf-preview-open]")).filter(
      (item) => item instanceof HTMLElement,
    );
    const pdfDocumentUrl = overlay.dataset.pdfDocumentUrl || "";
    const pageNumbers = (overlay.dataset.pdfPageNumbers || "")
      .split(",")
      .map((value) => Number.parseInt(value, 10))
      .filter((value) => Number.isInteger(value) && value > 0);
    const pageLabels = (overlay.dataset.pdfPageLabels || "")
      .split(",")
      .map((value) => Number.parseInt(value, 10))
      .filter((value) => Number.isInteger(value) && value > 0);

    if (
      !previewItems.length ||
      !(documentFrame instanceof HTMLObjectElement) ||
      !pdfDocumentUrl ||
      !pageNumbers.length
    ) {
      return;
    }

    let currentIndex = 0;
    let lastTrigger = null;

    const clampIndex = (index) => Math.max(0, Math.min(pageNumbers.length - 1, index));
    const buildViewerSrc = (pageNumber) => `${pdfDocumentUrl}#page=${pageNumber}&view=FitH`;

    const renderPreview = () => {
      const pageNumber = pageNumbers[currentIndex];
      const pageLabel = pageLabels[currentIndex] || pageNumber;
      if (!Number.isInteger(pageNumber)) {
        return;
      }

      const viewerSrc = buildViewerSrc(pageNumber);
      documentFrame.data = viewerSrc;
      documentFrame.setAttribute("data", viewerSrc);
      documentFrame.title = `PDF 第 ${pageNumber} 頁`;

      if (counter) {
        counter.textContent = `第 ${pageNumber} 頁 / 共 ${pageNumbers.length} 頁`;
      }
      if (prevButton instanceof HTMLButtonElement) {
        prevButton.disabled = currentIndex <= 0;
      }
      if (nextButton instanceof HTMLButtonElement) {
        nextButton.disabled = currentIndex >= pageNumbers.length - 1;
      }
    };

    const openPreview = (index, trigger = null) => {
      currentIndex = clampIndex(index);
      lastTrigger = trigger;
      renderPreview();
      overlay.hidden = false;
      overlay.setAttribute("aria-hidden", "false");
      document.body.classList.add("is-overlay-open");
      if (dialog instanceof HTMLElement) {
        dialog.focus({ preventScroll: true });
      }
    };

    const closePreview = () => {
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
      document.body.classList.remove("is-overlay-open");
      if (lastTrigger instanceof HTMLElement) {
        lastTrigger.focus({ preventScroll: true });
      }
    };

    const movePreview = (delta) => {
      const nextIndex = currentIndex + delta;
      if (nextIndex < 0 || nextIndex >= pageNumbers.length) {
        return;
      }
      currentIndex = nextIndex;
      renderPreview();
    };

    previewItems.forEach((item, index) => {
      const pageIndex = Number.parseInt(item.dataset.pdfPageIndex || String(index), 10);
      const safeIndex = Number.isInteger(pageIndex) ? clampIndex(pageIndex) : clampIndex(index);

      item.addEventListener("click", () => openPreview(safeIndex, item));
      item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openPreview(safeIndex, item);
        }
      });
    });

    closeButtons.forEach((button) => {
      button.addEventListener("click", closePreview);
    });

    prevButton?.addEventListener("click", () => movePreview(-1));
    nextButton?.addEventListener("click", () => movePreview(1));
    fullscreenButton?.addEventListener("click", async () => {
      if (!(dialog instanceof HTMLElement) || !dialog.requestFullscreen) {
        return;
      }
      try {
        if (document.fullscreenElement === dialog && document.exitFullscreen) {
          await document.exitFullscreen();
        } else {
          await dialog.requestFullscreen();
        }
      } catch (_error) {}
    });

    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closePreview();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        movePreview(-1);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        movePreview(1);
      }
    });
  }

  initLoader();
  initMagneticButtons();
  initHeaderBehavior();
  initPointerGlow();
  initExpandableSections();
  initSubmitLoaders();
  rebindImportSubmitLoaders();
  initTaskTimerV3();
  initPdfPreview();
  initAmbientSketch();
})();
