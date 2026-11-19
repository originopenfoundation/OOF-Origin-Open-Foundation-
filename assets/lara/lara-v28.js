(() => {
  'use strict';
  const root=document.getElementById('lara-root');
  if(!root||root.dataset.v28CleanChat==='true')return;
  root.dataset.v28CleanChat='true';
  const head=root.querySelector('.lara-head'),messages=root.querySelector('.lara-messages'),form=root.querySelector('.lara-form');
  const input=root.querySelector('.lara-input'),status=root.querySelector('.lara-status'),avatar=root.querySelector('.lara-avatar-2d'),avatarState=root.querySelector('.lara-avatar-state');
  const visitorTitle='OOF Methodology AI Assistant';
  const visitorPrivacy = () => root.querySelector('.lara-language')?.value === 'sk'
    ? 'Použiť Groq pre túto odpoveď. Môže dostať správu aj nedávny kontext. Iba verejný, necitlivý obsah.'
    : 'Use Groq for this reply. It may receive your message and recent chat. Public, non-sensitive content only.';
  root.querySelector('.lara-title').textContent=visitorTitle;
  root.querySelector('.lara-live')?.setAttribute('hidden','');

  // Keep advanced workflow settings available, but never place them in the default visitor view.
  const settings=document.createElement('details');settings.className='lara-settings-panel';
  settings.innerHTML='<summary>Conversation settings</summary><div class="lara-settings-body"></div>';
  const settingsBody=settings.querySelector('.lara-settings-body');
  const controls=root.querySelector('.lara-controls'),style=root.querySelector('.lara-style-label');
  if(controls)settingsBody.append(controls);
  if(style)settingsBody.append(style);
  const trace=root.querySelector('.lara-trace');
  if(trace)settingsBody.append(trace);
  head.insertAdjacentElement('afterend',settings);
  root.querySelector('.lara-recognize')?.setAttribute('hidden','');
  root.querySelector('.lara-restore')?.setAttribute('hidden','');
  root.querySelector('.lara-new').textContent='New chat';
  root.querySelector('.lara-footer span')?.setAttribute('hidden','');

  const consent=root.querySelector('.lara-provider-consent-label');
  if(consent){
    consent.classList.add('lara-privacy-consent');
    const copy=consent.querySelector('span');
    if(copy)copy.textContent=visitorPrivacy();
  }
  const refreshPrivacyCopy = () => {
    const copy = consent?.querySelector('span');
    const disclosure = visitorPrivacy();
    if (copy && copy.textContent !== disclosure) copy.textContent = disclosure;
  };
  const refreshVisitorLabels=()=>{const title=root.querySelector('.lara-title');if(title&&title.textContent!==visitorTitle)title.textContent=visitorTitle;refreshPrivacyCopy();const fresh=root.querySelector('.lara-new');if(fresh&&fresh.textContent!=='New chat')fresh.textContent='New chat';};
  root.querySelector('.lara-language')?.addEventListener('change',refreshPrivacyCopy);
  new MutationObserver(refreshVisitorLabels).observe(head,{childList:true,subtree:true,characterData:true});
  if(consent)new MutationObserver(refreshPrivacyCopy).observe(consent,{childList:true,subtree:true,characterData:true});
  refreshVisitorLabels();

  const preview = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)
    && new URLSearchParams(location.search).get('laraAvatar') === 'prototype';
  if (preview && avatar) {
    avatar.insertAdjacentHTML('beforeend', `
      <svg class="lara-avatar-prototype" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
        <defs><linearGradient id="lara-avatar-background" x2="1" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="#496b7a"/><stop offset="1" stop-color="#233245"/></linearGradient></defs>
        <rect width="100" height="100" fill="url(#lara-avatar-background)"/>
        <path class="lara-avatar-body" d="M0 100c2-16 16-21 37-27h26c21 6 35 11 37 27z" fill="#111a28"/>
        <path d="M36 63h28v16L50 87 36 79z" fill="#a97762"/>
        <path d="M26 79l11-5 13 13 13-13 11 5-11 21H37z" fill="#202c3d"/>
        <g class="lara-avatar-head">
          <path d="M21 47C12 19 30 6 51 6c24 0 40 19 28 46L65 74H36z" fill="#100f16"/>
          <path d="M24 44c-9-4-7 13 2 15m50-15c9-4 7 13-2 15" fill="#b48169"/>
          <path d="M24 33c2-15 13-22 27-22 17 0 26 10 26 25v12c-1 18-12 31-26 32-12 0-26-15-27-32z" fill="#d4a185"/>
          <path d="M50 76c14-4 21-18 23-31l3-12 1 15c-1 18-12 31-26 32-5 0-11-3-14-7 4 3 8 4 13 3z" fill="#b9826e"/>
          <path d="M18 43C12 16 32 3 56 7c18 2 29 16 25 38l-7 4c1-13-6-18-14-28-13 12-24 8-38 26l7-16z" fill="#15141b"/>
          <path d="M22 29c7-14 20-18 37-18-10 5-19 9-34 20m42-15c7 4 11 12 12 21" fill="none" stroke="#3c3b47" stroke-width="1.7" stroke-linecap="round"/>
          <path class="lara-avatar-brows" d="M29 41q7-4 14-1m14 0q8-4 14 0" fill="none" stroke="#382826" stroke-width="2" stroke-linecap="round"/>
          <g class="lara-avatar-eyes">
            <path d="M29 48q7-6 15 0-7 6-15 0m28 0q7-6 15 0-7 6-15 0" fill="#fff1e6"/>
            <g class="lara-avatar-gaze" fill="#382625">
              <ellipse cx="37" cy="48" rx="3.1" ry="3.5"/><ellipse cx="64" cy="48" rx="3.1" ry="3.5"/>
              <path d="M37 46h1m26 0h1" stroke="#fff"/>
            </g>
            <path d="M29 48q7-6 15 0m13 0q7-6 15 0" fill="none" stroke="#492f2b" stroke-width="1.3"/>
          </g>
          <path class="lara-avatar-lids" d="M29 48q7 4 15 0m13 0q7 4 15 0" fill="none" stroke="#492f2b" stroke-width="1.7" stroke-linecap="round"/>
          <path d="M23 44l5 1m45 0 6-2M27 44q9-3 19 0l-1 8q-1 4-5 4h-7q-5 0-6-5zm28 0q10-3 19 0v7q-1 5-6 5h-7q-4 0-5-4zm-9 2q5-3 9 0" fill="none" stroke="#171925" stroke-width="1.8" stroke-linejoin="round"/>
          <path d="M50 49l-3 10q2 2 6 0" fill="none" stroke="#ab755e" stroke-width="1.4" stroke-linecap="round"/>
          <path class="lara-avatar-lips" d="M42 65q4-1 8 0 5-1 9-2-4 6-9 6-4 0-8-4z" fill="#97534e"/>
          <ellipse class="lara-avatar-mouth" cx="50" cy="65" rx="7" ry="4" fill="#5f3035"/>
        </g>
      </svg>`);
    avatar.classList.add('lara-avatar-preview');
  }
  const mouth = avatar?.querySelector('.lara-avatar-mouth');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let mouthTimer;
  const closeMouth = () => {
    clearTimeout(mouthTimer);
    mouth?.style.removeProperty('--lara-mouth-opening');
  };
  const moveMouth = (playback, opening = 0.76) => {
    closeMouth();
    if (!mouth || reducedMotion.matches) return;
    // Native synthesis provides no audio stream. Boundaries align the next movement
    // when available, with a speech-activity approximation between events.
    mouth.style.setProperty('--lara-mouth-opening', opening);
    mouthTimer = setTimeout(() => {
      if (utterance !== playback || root.dataset.avatarState !== 'speaking') {
        closeMouth();
        return;
      }
      moveMouth(playback, opening > 0.4 ? 0.19 : opening > 0.15 ? 0.48 : 0.66);
    }, opening > 0.4 ? 130 : 95);
  };
  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches) closeMouth();
    else if (utterance && root.dataset.avatarState === 'speaking') moveMouth(utterance);
  });
  const setState=(next,label)=>{
    root.dataset.avatarState=next;
    if(avatar)avatar.setAttribute('aria-label','LaRA is '+label);
    if(avatarState)avatarState.textContent=label;
  };
  const voiceStop=document.createElement('button');voiceStop.type='button';voiceStop.className='lara-voice-stop';voiceStop.hidden=true;voiceStop.textContent='Stop voice';voiceStop.setAttribute('aria-label','Stop voice activity');
  root.querySelector('.lara-actions')?.prepend(voiceStop);
  let recognition = null;
  let utterance = null;
  let voiceTimeout;
  let voiceTrigger;
  const setVoicePending = active => {
    clearTimeout(voiceTimeout);
    voiceStop.hidden = !active;
  };
  const resetVoice = () => {
    const capture = recognition;
    const playback = utterance;
    recognition = null;
    utterance = null;
    voiceTrigger = null;
    setVoicePending(false);
    closeMouth();
    try { capture?.abort(); } catch {}
    if (playback) window.speechSynthesis.cancel();
  };
  const announce = text => { if (status) status.textContent = text; };
  const ready = () => {
    closeMouth();
    setState(root.classList.contains('is-processing') ? 'thinking' : 'idle',
      root.classList.contains('is-processing') ? 'Thinking' : 'Ready');
    if (!root.classList.contains('is-processing')) announce('');
  };
  const stopVoice = () => {
    resetVoice();
    ready();
  };
  const voiceError = (label, message) => {
    resetVoice();
    setState('error', label);
    announce(message);
  };
  const locale = () => {
    const language = root.querySelector('.lara-language')?.value;
    return !language || language === 'auto' ? navigator.language || 'en'
      : ({zh:'zh-CN', ja:'ja-JP', ko:'ko-KR', sk:'sk-SK'}[language] || language);
  };
  voiceStop.addEventListener('click', () => {
    const trigger = voiceTrigger;
    stopVoice();
    trigger?.focus({preventScroll:true});
  });
  const listenButton = root.querySelector('.lara-listen');
  const voiceNotice = document.createElement('small');
  voiceNotice.className = 'lara-voice-notice';
  voiceNotice.textContent = 'Your browser may send microphone audio to its speech recognition service.';
  if (listenButton) {
    voiceNotice.id = 'lara-voice-notice';
    listenButton.setAttribute('aria-describedby', voiceNotice.id);
    settingsBody.append(voiceNotice);
  }
  const viewport = window.visualViewport;
  const fitViewport = () => {
    if (!viewport) return;
    const keyboardInset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
    root.style.setProperty('--lara-viewport-height', viewport.height + 'px');
    root.style.setProperty('--lara-viewport-inset', keyboardInset + 'px');
  };
  viewport?.addEventListener('resize', fitViewport);
  viewport?.addEventListener('scroll', fitViewport);
  window.addEventListener('resize', fitViewport);
  window.addEventListener('pagehide', () => {
    if (recognition || utterance) stopVoice();
  });
  fitViewport();
  if (listenButton) listenButton.hidden = !(window.SpeechRecognition||window.webkitSpeechRecognition);

  root.addEventListener('click', event => {
    if (event.target.closest('.lara-close, .lara-new, .lara-clear') && (recognition || utterance)) stopVoice();
    if (event.target.closest('.lara-listen')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const Recognition = window.SpeechRecognition||window.webkitSpeechRecognition;
      if (!Recognition) {
        voiceError('Voice input error', 'Voice input is not available in this browser.');
        return;
      }
      if (recognition) { stopVoice(); return; }
      stopVoice();
      let capture;
      try { capture = new Recognition(); }
      catch {
        voiceError('Voice input error', 'Voice input could not be started.');
        return;
      }
      voiceTrigger = listenButton;
      recognition = capture;
      setVoicePending(true);
      announce('Starting voice input… Your browser may use its speech recognition service.');
      voiceTimeout = setTimeout(() => {
        if (recognition === capture) voiceError('Voice input error', 'Voice input timed out.');
      }, 30000);
      let transcript = '';
      capture.lang = locale();
      capture.interimResults = false;
      capture.onaudiostart = () => {
        if (recognition !== capture) return;
        setState('listening', 'Listening');
        announce('Listening...');
      };
      capture.onresult = result => {
        if (recognition !== capture) return;
        transcript = Array.from(result.results).filter(item => item.isFinal)
          .map(item => item[0].transcript).join(' ').trim();
      };
      capture.onerror = result => {
        if (recognition !== capture) return;
        const errors = {
          'not-allowed': 'Microphone permission was denied.',
          'service-not-allowed': 'The browser speech recognition service is unavailable.',
          'audio-capture': 'No usable microphone was found.',
          'no-speech': 'No speech was detected.'
        };
        voiceError('Voice input error', errors[result.error] || 'Voice input could not be completed.');
      };
      capture.onend = () => {
        if (recognition !== capture) return;
        recognition = null;
        voiceTrigger = null;
        setVoicePending(false);
        if (transcript) {
          const draft = input.value.trimEnd();
          input.value = [draft, transcript].filter(Boolean).join(' ').slice(0, input.maxLength);
          input.dispatchEvent(new Event('input', {bubbles:true}));
          ready();
          announce('Transcript ready to review and send.');
        } else {
          voiceError('Voice input error', 'No speech was transcribed.');
        }
      };
      try { capture.start(); }
      catch {
        voiceError('Voice input error', 'Voice input could not be started.');
      }
      return;
    }
    const speak = event.target.closest('.lara-speak');
    if (!speak) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
      voiceError('Voice output error', 'Voice output is not available in this browser.');
      return;
    }
    const text = speak.closest('.lara-message')?.querySelector('.lara-prose')?.textContent?.trim();
    if (!text) return;
    stopVoice();
    const playback = new SpeechSynthesisUtterance(text);
    voiceTrigger = speak;
    utterance = playback;
    setVoicePending(true);
    announce('Starting speech…');
    playback.lang = speak.dataset.speechLocale || locale();
    voiceTimeout = setTimeout(() => {
      if (utterance === playback) voiceError('Voice output error', 'Speech did not start.');
    }, 15000);
    playback.onstart = () => {
      if (utterance !== playback) return;
      clearTimeout(voiceTimeout);
      setState('speaking', 'Speaking');
      announce('Speaking...');
      moveMouth(playback);
    };
    playback.onboundary = () => {
      if (utterance === playback && root.dataset.avatarState === 'speaking') moveMouth(playback, 0.9);
    };
    playback.onpause = () => {
      if (utterance !== playback) return;
      ready();
    };
    playback.onresume = playback.onstart;
    playback.onend = () => {
      if (utterance !== playback) return;
      utterance = null;
      voiceTrigger = null;
      setVoicePending(false);
      ready();
    };
    playback.onerror = () => {
      if (utterance !== playback) return;
      voiceError('Voice output error', 'Voice output could not be completed.');
    };
    try { window.speechSynthesis.speak(playback); }
    catch { playback.onerror(); }
  }, true);
  const declutterWelcome=()=>{
    const welcome=messages?.querySelector('.lara-welcome');if(!welcome||welcome.dataset.cleanWelcome)return;
    welcome.dataset.cleanWelcome='true';welcome.querySelector('.lara-welcome-avatar')?.remove();welcome.querySelector('.lara-starters')?.remove();
    const prose=welcome.querySelector('.lara-prose');if(prose)prose.textContent='How can I help with OOF methodology?';
  };
  const observer=new MutationObserver(declutterWelcome);
  if(messages)observer.observe(messages,{childList:true,subtree:true});declutterWelcome();
  form?.addEventListener('submit', () => { if (recognition || utterance) stopVoice(); }, true);
  form?.addEventListener('submit', () => {
    if (root.classList.contains('is-processing')) settings.open = false;
  });
  window.LaRACleanChat={stopVoice,settings:()=>settings.open=true};
})();
