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

      form.addEventListener("submit", () => {
        form.classList.add("is-submitting");
        if (overlay) {
          overlay.hidden = false;
        }

        submitControls.forEach((control) => {
          const loadingText = control.dataset.loadingText || fallbackText;
          control.disabled = true;
          control.setAttribute("aria-busy", "true");

          if (control instanceof HTMLInputElement) {
            control.value = loadingText;
            return;
          }

          control.textContent = loadingText;
        });
      });
    });
  }

  function initTaskTimer() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:${taskId}`;
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
      running: false,
      paused: false,
      expired: false,
      finished: false,
      lastUpdatedAt: 0,
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

    const setTimerClasses = (variant) => {
      timerRoot.classList.toggle("is-running", variant === "running");
      timerRoot.classList.toggle("is-expired", variant === "expired");
      timerRoot.classList.toggle("is-finished", variant === "finished");
      timerRoot.classList.toggle("is-paused", variant === "paused");
    };

    const saveState = () => {
      try {
        if (state.running || state.paused) {
          window.localStorage.setItem(storageKey, JSON.stringify(state));
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const clearState = () => {
      try {
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
          return;
        }
        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.lastUpdatedAt = safeNumber(parsed.lastUpdatedAt, Date.now());
        state.chimed = false;
      } catch (_error) {}
    };

    const formatClock = (totalSeconds) => {
      const safeSeconds = Math.max(0, Math.floor(totalSeconds));
      const minutes = Math.floor(safeSeconds / 60);
      const seconds = safeSeconds % 60;
      return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    };

    const setBadge = (text, variant) => {
      if (!stateBadge) {
        return;
      }
      stateBadge.textContent = text;
      stateBadge.className = `status-pill ${timerStateClassMap[variant] || timerStateClassMap.idle}`;
    };

    const stopTicker = () => {
      if (timerHandle) {
        window.clearInterval(timerHandle);
        timerHandle = 0;
      }
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

    const syncElapsed = () => {
      if (!state.running) {
        return;
      }

      const now = Date.now();
      const elapsedSeconds = Math.floor((now - state.lastUpdatedAt) / 1000);
      if (elapsedSeconds <= 0) {
        return;
      }

      state.remainingSeconds = Math.max(0, state.remainingSeconds - elapsedSeconds);
      state.lastUpdatedAt = now;

      if (state.remainingSeconds === 0) {
        state.running = false;
        state.paused = false;
        state.expired = true;
        clearState();
      }
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.lastUpdatedAt = nextState.lastUpdatedAt;
      state.chimed = nextState.chimed;
      stopTicker();
      clearState();
    };

    const renderTimer = () => {
      syncElapsed();

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
        setBadge("進行中", "running");
        if (caption) {
          caption.textContent = "時鐘正在走，可以隨時暫停、延長或結束。";
        }
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到", "expired");
        if (caption) {
          caption.textContent = "這一輪時間已到，可以延長或直接整理完成記錄。";
        }
        document.title = `[時間到] ${baseTitle}`;
        if (!state.chimed) {
          playChime();
          state.chimed = true;
        }
      } else if (state.finished) {
        setBadge("已提前結束", "finished");
        if (caption) {
          caption.textContent = "這一輪計時已手動結束，可以直接提交學習完成。";
        }
        document.title = baseTitle;
      } else if (state.paused) {
        setBadge("已暫停", "paused");
        if (caption) {
          caption.textContent = "已暫停，可以繼續這一輪或重新設定時間。";
        }
        document.title = baseTitle;
      } else {
        setBadge("未開始", "idle");
        if (caption) {
          caption.textContent = "先設定分鐘，再開始。";
        }
        document.title = baseTitle;
      }

      if (minutesInput && !state.running && !state.paused && !state.expired) {
        minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
      }

      if (pauseButton) {
        pauseButton.disabled = !state.running && !state.paused;
        pauseButton.textContent = state.paused ? "繼續" : "暫停";
      }
      if (startButton) {
        startButton.textContent = state.paused ? "重新開始" : "開始計時";
      }

      presetButtons.forEach((button) => {
        button.disabled = state.running;
      });
      if (minutesInput) {
        minutesInput.disabled = state.running;
      }
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
      }, 250);
    };

    const applyMinutesFromInput = () => {
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      stopTicker();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        state.running = false;
        state.paused = true;
        stopTicker();
        renderTimer();
        return;
      }
      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = clampMinutes(extraMinutes) * 60;
      state.durationSeconds += extraSeconds;
      state.remainingSeconds += extraSeconds;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      if (!state.running) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
      }
      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.lastUpdatedAt = Date.now();
      stopTicker();
      renderTimer();

      const summaryField = completeForm ? completeForm.querySelector("textarea[name='summary_text']") : null;
      if (completeForm) {
        completeForm.scrollIntoView({ behavior: effectiveMotionLevel === "minimal" ? "auto" : "smooth", block: "start" });
      }
      if (summaryField instanceof HTMLElement) {
        window.setTimeout(() => summaryField.focus(), 120);
      }
    };

    loadState();
    if (minutesInput && !state.running && !state.paused && !state.expired && !state.finished) {
      minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
    }
    if (state.running) {
      syncElapsed();
      if (state.running) {
        startTicker();
      }
    }
    renderTimer();

    if (minutesInput) {
      minutesInput.addEventListener("change", applyMinutesFromInput);
    }
    startButton?.addEventListener("click", startTimer);
    pauseButton?.addEventListener("click", togglePause);
    resetButton?.addEventListener("click", applyMinutesFromInput);
    finishButton?.addEventListener("click", finishEarly);

    presetButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (!minutesInput) {
          return;
        }
        minutesInput.value = String(clampMinutes(button.dataset.timerPreset));
        applyMinutesFromInput();
      });
    });

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

  function initTaskTimerV2() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:${taskId}`;
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
      running: false,
      paused: false,
      expired: false,
      finished: false,
      lastUpdatedAt: 0,
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

    const setTimerClasses = (variant) => {
      timerRoot.classList.toggle("is-running", variant === "running");
      timerRoot.classList.toggle("is-expired", variant === "expired");
      timerRoot.classList.toggle("is-finished", variant === "finished");
      timerRoot.classList.toggle("is-paused", variant === "paused");
    };

    const saveState = () => {
      try {
        if (state.running || state.paused) {
          window.localStorage.setItem(storageKey, JSON.stringify(state));
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const clearState = () => {
      try {
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
          return;
        }
        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.lastUpdatedAt = safeNumber(parsed.lastUpdatedAt, Date.now());
        state.chimed = false;
      } catch (_error) {}
    };

    const formatClock = (totalSeconds) => {
      const safeSeconds = Math.max(0, Math.floor(totalSeconds));
      const minutes = Math.floor(safeSeconds / 60);
      const seconds = safeSeconds % 60;
      return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    };

    const setBadge = (text, variant) => {
      if (!stateBadge) {
        return;
      }
      stateBadge.textContent = text;
      stateBadge.className = `status-pill ${timerStateClassMap[variant] || timerStateClassMap.idle}`;
    };

    const stopTicker = () => {
      if (timerHandle) {
        window.clearInterval(timerHandle);
        timerHandle = 0;
      }
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

    const syncElapsed = () => {
      if (!state.running) {
        return;
      }

      const now = Date.now();
      const elapsedSeconds = Math.floor((now - state.lastUpdatedAt) / 1000);
      if (elapsedSeconds <= 0) {
        return;
      }

      state.remainingSeconds = Math.max(0, state.remainingSeconds - elapsedSeconds);
      state.lastUpdatedAt = now;

      if (state.remainingSeconds === 0) {
        state.running = false;
        state.paused = false;
        state.expired = true;
        clearState();
      }
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.lastUpdatedAt = nextState.lastUpdatedAt;
      state.chimed = nextState.chimed;
      stopTicker();
      clearState();
    };

    const renderTimer = () => {
      syncElapsed();

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
        setBadge("進行中", "running");
        setTimerClasses("running");
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到", "expired");
        setTimerClasses("expired");
        document.title = `[時間到] ${baseTitle}`;
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
        setBadge("未開始", "idle");
        setTimerClasses("idle");
        document.title = baseTitle;
      }

      if (minutesInput && !state.running) {
        minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
        minutesInput.disabled = false;
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
      if (minutesInput) {
        minutesInput.disabled = state.running;
      }
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
      }, 250);
    };

    const applyMinutesFromInput = () => {
      resetToIdle();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        state.running = false;
        state.paused = true;
        stopTicker();
        renderTimer();
        return;
      }
      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = Math.max(60, Math.round(safeNumber(extraMinutes, 10)) * 60);
      state.durationSeconds += extraSeconds;
      state.remainingSeconds += extraSeconds;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      if (!state.running) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
      }
      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.lastUpdatedAt = Date.now();
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

    loadState();
    if (state.running) {
      syncElapsed();
      if (state.expired) {
        stopTicker();
      } else {
        startTicker();
      }
    }
    if (minutesInput && !state.running && !state.paused && !state.expired && !state.finished) {
      minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
    }
    renderTimer();

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

  function initTaskTimerV2() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:v2:${taskId}`;
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
      running: false,
      paused: false,
      expired: false,
      finished: false,
      lastUpdatedAt: 0,
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
          window.localStorage.setItem(storageKey, JSON.stringify(state));
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }

        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
          return;
        }

        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.lastUpdatedAt = safeNumber(parsed.lastUpdatedAt, Date.now());
        state.chimed = false;
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

    const syncElapsed = () => {
      if (!state.running) {
        return;
      }

      const now = Date.now();
      const elapsedSeconds = Math.floor((now - state.lastUpdatedAt) / 1000);
      if (elapsedSeconds <= 0) {
        return;
      }

      state.remainingSeconds = Math.max(0, state.remainingSeconds - elapsedSeconds);
      state.lastUpdatedAt = now;

      if (state.remainingSeconds === 0) {
        state.running = false;
        state.paused = false;
        state.expired = true;
        clearState();
      }
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.lastUpdatedAt = nextState.lastUpdatedAt;
      state.chimed = nextState.chimed;
      stopTicker();
      clearState();
    };

    const renderTimer = () => {
      syncElapsed();

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
        setBadge("進行中", "running");
        setTimerClasses("running");
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到", "expired");
        setTimerClasses("expired");
        document.title = `[時間到] ${baseTitle}`;
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
      }, 250);
    };

    const applyMinutesFromInput = () => {
      resetToIdle();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        state.running = false;
        state.paused = true;
        stopTicker();
        renderTimer();
        return;
      }

      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = Math.max(60, Math.round(safeNumber(extraMinutes, 10)) * 60);
      state.durationSeconds += extraSeconds;
      state.remainingSeconds += extraSeconds;
      state.expired = false;
      state.finished = false;
      state.chimed = false;

      if (!state.running) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
      }

      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.lastUpdatedAt = Date.now();
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
      window.localStorage.removeItem(`ls-task-timer:${taskId}`);
    } catch (_error) {}

    clearState();
    resetToIdle(defaultMinutes);
    renderTimer();

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

  function initTaskTimerV2() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:${taskId}`;
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
      running: false,
      paused: false,
      expired: false,
      finished: false,
      lastUpdatedAt: 0,
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

    const setTimerClasses = (variant) => {
      timerRoot.classList.toggle("is-running", variant === "running");
      timerRoot.classList.toggle("is-expired", variant === "expired");
      timerRoot.classList.toggle("is-finished", variant === "finished");
      timerRoot.classList.toggle("is-paused", variant === "paused");
    };

    const saveState = () => {
      try {
        if (state.running || state.paused) {
          window.localStorage.setItem(storageKey, JSON.stringify(state));
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const clearState = () => {
      try {
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
          return;
        }
        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.lastUpdatedAt = safeNumber(parsed.lastUpdatedAt, Date.now());
        state.chimed = false;
      } catch (_error) {}
    };

    const formatClock = (totalSeconds) => {
      const safeSeconds = Math.max(0, Math.floor(totalSeconds));
      const minutes = Math.floor(safeSeconds / 60);
      const seconds = safeSeconds % 60;
      return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    };

    const setBadge = (text, variant) => {
      if (!stateBadge) {
        return;
      }
      stateBadge.textContent = text;
      stateBadge.className = `status-pill ${timerStateClassMap[variant] || timerStateClassMap.idle}`;
    };

    const stopTicker = () => {
      if (timerHandle) {
        window.clearInterval(timerHandle);
        timerHandle = 0;
      }
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

    const syncElapsed = () => {
      if (!state.running) {
        return;
      }

      const now = Date.now();
      const elapsedSeconds = Math.floor((now - state.lastUpdatedAt) / 1000);
      if (elapsedSeconds <= 0) {
        return;
      }

      state.remainingSeconds = Math.max(0, state.remainingSeconds - elapsedSeconds);
      state.lastUpdatedAt = now;

      if (state.remainingSeconds === 0) {
        state.running = false;
        state.paused = false;
        state.expired = true;
        clearState();
      }
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.lastUpdatedAt = nextState.lastUpdatedAt;
      state.chimed = nextState.chimed;
      stopTicker();
      clearState();
    };

    const renderTimer = () => {
      syncElapsed();

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
        setBadge("進行中", "running");
        setTimerClasses("running");
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到", "expired");
        setTimerClasses("expired");
        document.title = `[時間到] ${baseTitle}`;
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
        setBadge("未開始", "idle");
        setTimerClasses("idle");
        document.title = baseTitle;
      }

      if (minutesInput && !state.running) {
        minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
        minutesInput.disabled = false;
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
      if (minutesInput) {
        minutesInput.disabled = state.running;
      }
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
      }, 250);
    };

    const applyMinutesFromInput = () => {
      resetToIdle();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        state.running = false;
        state.paused = true;
        stopTicker();
        renderTimer();
        return;
      }
      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = Math.max(60, Math.round(safeNumber(extraMinutes, 10)) * 60);
      state.durationSeconds += extraSeconds;
      state.remainingSeconds += extraSeconds;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      if (!state.running) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
      }
      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.lastUpdatedAt = Date.now();
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

    loadState();
    if (state.running) {
      syncElapsed();
      if (state.expired) {
        stopTicker();
      } else {
        startTicker();
      }
    }
    if (minutesInput && !state.running && !state.paused && !state.expired && !state.finished) {
      minutesInput.value = String(Math.max(1, Math.round(state.durationSeconds / 60)));
    }
    renderTimer();

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

  function initTaskTimerV2() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:v2:${taskId}`;
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
      running: false,
      paused: false,
      expired: false,
      finished: false,
      lastUpdatedAt: 0,
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
          window.localStorage.setItem(storageKey, JSON.stringify(state));
          return;
        }
        window.localStorage.removeItem(storageKey);
      } catch (_error) {}
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
          return;
        }
        state.durationSeconds = Math.max(60, safeNumber(parsed.durationSeconds, state.durationSeconds));
        state.remainingSeconds = Math.max(0, safeNumber(parsed.remainingSeconds, state.remainingSeconds));
        state.running = Boolean(parsed.running);
        state.paused = !state.running && Boolean(parsed.paused);
        state.expired = false;
        state.finished = false;
        state.lastUpdatedAt = safeNumber(parsed.lastUpdatedAt, Date.now());
        state.chimed = false;
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

    const syncElapsed = () => {
      if (!state.running) {
        return;
      }
      const now = Date.now();
      const elapsedSeconds = Math.floor((now - state.lastUpdatedAt) / 1000);
      if (elapsedSeconds <= 0) {
        return;
      }
      state.remainingSeconds = Math.max(0, state.remainingSeconds - elapsedSeconds);
      state.lastUpdatedAt = now;
      if (state.remainingSeconds === 0) {
        state.running = false;
        state.paused = false;
        state.expired = true;
        clearState();
      }
    };

    const resetToIdle = (minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes)) => {
      const nextState = buildIdleState(minutes);
      state.durationSeconds = nextState.durationSeconds;
      state.remainingSeconds = nextState.remainingSeconds;
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.lastUpdatedAt = nextState.lastUpdatedAt;
      state.chimed = nextState.chimed;
      stopTicker();
      clearState();
    };

    const renderTimer = () => {
      syncElapsed();
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
        setBadge("進行中", "running");
        setTimerClasses("running");
        document.title = baseTitle;
      } else if (state.expired) {
        setBadge("時間到", "expired");
        setTimerClasses("expired");
        document.title = `[時間到] ${baseTitle}`;
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
      }, 250);
    };

    const applyMinutesFromInput = () => {
      resetToIdle();
      renderTimer();
    };

    const startTimer = () => {
      ensureAudioContext();
      const minutes = clampMinutes(minutesInput ? minutesInput.value : defaultMinutes);
      state.durationSeconds = minutes * 60;
      state.remainingSeconds = minutes * 60;
      state.running = true;
      state.paused = false;
      state.expired = false;
      state.finished = false;
      state.lastUpdatedAt = Date.now();
      state.chimed = false;
      startTicker();
      renderTimer();
    };

    const togglePause = () => {
      if (state.running) {
        state.running = false;
        state.paused = true;
        stopTicker();
        renderTimer();
        return;
      }
      if (state.paused) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
        renderTimer();
      }
    };

    const extendTimer = (extraMinutes) => {
      const extraSeconds = Math.max(60, Math.round(safeNumber(extraMinutes, 10)) * 60);
      state.durationSeconds += extraSeconds;
      state.remainingSeconds += extraSeconds;
      state.expired = false;
      state.finished = false;
      state.chimed = false;
      if (!state.running) {
        ensureAudioContext();
        state.running = true;
        state.paused = false;
        state.lastUpdatedAt = Date.now();
        startTicker();
      }
      renderTimer();
    };

    const finishEarly = () => {
      state.running = false;
      state.paused = false;
      state.expired = false;
      state.finished = true;
      state.remainingSeconds = 0;
      state.lastUpdatedAt = Date.now();
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
      window.localStorage.removeItem(`ls-task-timer:${taskId}`);
    } catch (_error) {}

    loadState();
    if (state.running) {
      syncElapsed();
      if (state.expired) {
        stopTicker();
      } else {
        startTicker();
      }
    }
    renderTimer();

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

  function initTaskTimerV3() {
    const timerRoot = document.querySelector("[data-task-timer]");
    if (!timerRoot) {
      return;
    }

    const taskId = timerRoot.dataset.taskId || "study-task";
    const storageKey = `ls-task-timer:v3:${taskId}`;
    const legacyKeys = [`ls-task-timer:${taskId}`, `ls-task-timer:v2:${taskId}`];
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
      state.running = nextState.running;
      state.paused = nextState.paused;
      state.expired = nextState.expired;
      state.finished = nextState.finished;
      state.chimed = nextState.chimed;
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
    };

    const loadState = () => {
      try {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
          return;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || (!parsed.running && !parsed.paused)) {
          clearState();
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
    if (state.running) {
      if (state.expired) {
        stopTicker();
      } else {
        startTicker();
      }
    }
    renderTimer();

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

  initLoader();
  initMagneticButtons();
  initHeaderBehavior();
  initPointerGlow();
  initExpandableSections();
  initSubmitLoaders();
  initTaskTimerV3();
  initAmbientSketch();
})();
