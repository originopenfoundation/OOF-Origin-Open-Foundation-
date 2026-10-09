#!/usr/bin/env python3
"""Build reviewed public-language access layers without translating normative OOF material."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://originopenfoundation.org/"

LANGUAGES = {
    "de": {"code": "de-DE", "native": "Deutsch", "english": "German"},
    "zh-cn": {"code": "zh-CN", "native": "简体中文（中国大陆）", "english": "Simplified Chinese (Mainland China)"},
    "zh-hk": {"code": "zh-HK", "native": "繁體中文（香港）", "english": "Traditional Chinese (Hong Kong)"},
    "ja": {"code": "ja-JP", "native": "日本語", "english": "Japanese"},
    "es": {"code": "es-ES", "native": "Español", "english": "Spanish"},
    "pt": {"code": "pt-PT", "native": "Português", "english": "Portuguese"},
    "fr": {"code": "fr-FR", "native": "Français", "english": "French"},
    "hi": {"code": "hi-IN", "native": "हिन्दी", "english": "Hindi"},
    "ko": {"code": "ko-KR", "native": "한국어", "english": "Korean"},
    "ru": {"code": "ru-RU", "native": "Русский", "english": "Russian"},
    "it": {"code": "it-IT", "native": "Italiano", "english": "Italian"},
    "ar": {"code": "ar", "native": "العربية", "english": "Arabic"},
}

TRANSLATIONS = {
    'it': {'description': 'Accesso in italiano a OOF® — OriginOpen® Foundation e alla sua infrastruttura metodologica.',
 'notice_title': 'Accesso in italiano',
 'notice': 'Questa pagina presenta in italiano le spiegazioni pubbliche di OOF®. La metodologia canonica, i '
           'termini protetti, i nomi delle architetture, gli standard, i moduli e gli identificatori '
           'rimangono invariati in inglese.',
 'canonical': 'Aprire la versione canonica in inglese',
 'hero': 'OOF® definisce le condizioni strutturali in cui i sistemi sono validi, interoperabili e allineati '
         'alla realtà.',
 'tagline': 'Standard Structured Reality™ per IA, sistemi e governance.',
 'validity': 'Un sistema è valido solo quando sono soddisfatte le condizioni strutturali definite.',
 'sections': [['Che cos’è OOF®',
               ['OOF® — OriginOpen® Foundation è un’autorità metodologica di riferimento che opera a livello '
                'di sistema.',
                'Definiamo come si stabiliscono il significato, la struttura e la validità nei sistemi umani '
                'e nell’intelligenza artificiale.',
                'Questa piattaforma è un sistema di riferimento canonico. Non implementa sistemi. Definisce '
                'le condizioni in cui i sistemi sono considerati validi.']],
              ['Modello di sistema',
               ['L’utilizzo è aperto. La compatibilità è condizionata. La validazione definisce l’integrità '
                'del sistema.',
                'Un sistema non è valido per il solo fatto di essere dichiarato tale. È valido solo quando '
                'sono soddisfatte le condizioni strutturali definite.']],
              ['Che cosa definiamo',
               [['condizioni di Structured Reality™',
                 'validità dei sistemi e stati operativi',
                 'significato canonico (UCL™)',
                 'interoperabilità tra sistemi',
                 'logica di sistema predisposta per la governance']]],
              ['Perché è importante',
               ['I sistemi moderni non falliscono per mancanza di tecnologia, ma per l’instabilità del '
                'significato e l’assenza di una struttura definita.',
                'L’IA interpreta in modo incoerente. I sistemi entrano in conflitto tra domini. Le decisioni '
                'mancano di un fondamento strutturale.',
                'Senza un significato definito, i sistemi non possono mantenere la propria validità.']],
              ['Modello di autorità',
               ['OOF® è un’autorità che non svolge funzioni esecutive.',
                'OOF® non gestisce sistemi e non impone risultati.',
                'OOF® definisce le condizioni strutturali in cui i sistemi rimangono coerenti, '
                'interoperabili e validi.']],
              ['IA e integrità dei sistemi',
               ['L’IA non definisce il significato. L’IA opera sulla base di un significato definito.',
                'Nell’ambito di OOF®, l’interpretazione è vincolata, il significato è canonico e i risultati '
                'sono verificabili sul piano strutturale.']],
              ['Global AI Incident Intelligence™',
               ['Gli incidenti reali legati all’IA sottopongono continuamente le architetture di governance '
                'a prove di stress.',
                'Monitora gli incidenti emergenti, comprendi le loro implicazioni per la governance e '
                'individua le architetture, gli standard e i moduli OOF® che governano la realtà operativa '
                'interessata.']],
              ['Esplora',
               ['Structured Reality™ · Standard · Utilizzo e validità · Compatibilità OOF® · Informazioni '
                'sull’autorità']],
              ['Dichiarazione conclusiva', ['OOF® non cerca il consenso. OOF® definisce la struttura.']]],
 'incident_link': 'Esplora AI Incident Intelligence →'},
    'ar': {'description': 'صفحة باللغة العربية للتعريف بـ OOF® — OriginOpen® Foundation وبنيتها التحتية المنهجية.',
 'notice_title': 'الوصول باللغة العربية',
 'notice': 'تقدم هذه الصفحة الشروح العامة لـ OOF® باللغة العربية. وتبقى المنهجية المرجعية المعتمدة '
           'والمصطلحات المحمية وأسماء البنى المعمارية والمعايير والوحدات والمعرّفات دون تغيير باللغة '
           'الإنجليزية.',
 'canonical': 'فتح النسخة الإنجليزية المرجعية المعتمدة',
 'hero': 'تحدد OOF® الشروط البنيوية التي تكون الأنظمة بموجبها صالحة وقابلة للتشغيل البيني ومتسقة مع الواقع.',
 'tagline': 'معايير Structured Reality™ للذكاء الاصطناعي والأنظمة والحوكمة.',
 'validity': 'لا يكون النظام صالحًا إلا عند استيفاء الشروط البنيوية المحددة.',
 'sections': [['ما هي OOF®؟',
               ['OOF® — OriginOpen® Foundation جهة مرجعية منهجية تعمل على مستوى الأنظمة.',
                'نحدد كيفية إرساء المعنى والبنية والصلاحية في الأنظمة البشرية والذكاء الاصطناعي.',
                'هذه المنصة نظام مرجعي معتمد. وهي لا تنفذ الأنظمة، بل تحدد الشروط التي تُعد الأنظمة بموجبها '
                'صالحة.']],
              ['نموذج النظام',
               ['الاستخدام مفتوح. والتوافق مشروط. والتحقق من الصلاحية يحدد سلامة النظام.',
                'لا يصبح النظام صالحًا بمجرد إعلان ذلك. ولا يكون صالحًا إلا عند استيفاء الشروط البنيوية '
                'المحددة.']],
              ['ما الذي نحدده؟',
               [['شروط Structured Reality™',
                 'صلاحية الأنظمة وحالاتها التشغيلية',
                 'المعنى المرجعي المعتمد (UCL™)',
                 'التشغيل البيني بين الأنظمة',
                 'منطق الأنظمة المهيأ للحوكمة']]],
              ['لماذا يُعد ذلك مهمًا؟',
               ['لا تفشل الأنظمة الحديثة بسبب نقص التكنولوجيا، بل بسبب عدم استقرار المعنى وغياب بنية محددة.',
                'يفسر الذكاء الاصطناعي المعلومات بصورة غير متسقة. وتتعارض الأنظمة عبر المجالات. وتفتقر '
                'القرارات إلى أساس بنيوي.',
                'من دون معنى محدد، لا تستطيع الأنظمة الحفاظ على صلاحيتها.']],
              ['نموذج الجهة المرجعية',
               ['OOF® جهة مرجعية لا تتولى التنفيذ المباشر.',
                'لا تشغّل OOF® الأنظمة ولا تفرض النتائج.',
                'تحدد OOF® الشروط البنيوية التي تظل الأنظمة بموجبها متسقة وقابلة للتشغيل البيني وصالحة.']],
              ['الذكاء الاصطناعي وسلامة الأنظمة',
               ['لا يحدد الذكاء الاصطناعي المعنى، بل يعمل بناءً على معنى محدد.',
                'في إطار OOF®، يكون التفسير مقيدًا، والمعنى مرجعيًا معتمدًا، والمخرجات قابلة للتحقق '
                'البنيوي.']],
              ['Global AI Incident Intelligence™',
               ['تخضع البنى المعمارية للحوكمة لاختبارات ضغط مستمرة من خلال حوادث الذكاء الاصطناعي في العالم '
                'الحقيقي.',
                'تابع الحوادث الناشئة، وافهم آثارها على الحوكمة، وتعرّف على البنى المعمارية والمعايير '
                'والوحدات التابعة لـ OOF® التي تحكم الواقع التشغيلي المتأثر.']],
              ['استكشف',
               ['Structured Reality™ · المعايير · الاستخدام والصلاحية · التوافق مع OOF® · نبذة عن الجهة '
                'المرجعية']],
              ['البيان الختامي', ['لا تسعى OOF® إلى الإجماع. بل تحدد البنية.']]],
 'incident_link': 'استكشف AI Incident Intelligence ←'},

    "ru": {
        "description": "Русскоязычная страница OOF® — OriginOpen® Foundation и её методологической инфраструктуры.",
        "notice_title": "Русскоязычная версия",
        "notice": "Эта страница представляет публичные пояснения OOF® на русском языке. Каноническая методология, охраняемые термины, названия архитектур, стандарты, модули и идентификаторы сохраняются без изменений на английском языке.",
        "canonical": "Открыть каноническую английскую версию",
        "hero": "OOF® определяет структурные условия, при которых системы являются валидными, совместимыми для взаимодействия и согласованными с реальностью.",
        "tagline": "Стандарты Structured Reality™ для ИИ, систем и управления.",
        "validity": "Система валидна только тогда, когда выполнены определённые структурные условия.",
        "sections": [
            ["Что такое OOF®", ["OOF® — OriginOpen® Foundation — методологический орган, устанавливающий эталонные определения на уровне систем.", "Мы определяем, как устанавливаются смысл, структура и валидность в человеческих системах и искусственном интеллекте.", "Эта платформа — каноническая справочная система. Она не реализует системы. Она определяет условия, при которых системы считаются валидными."]],
            ["Модель системы", ["Использование открыто. Совместимость обусловлена выполнением требований. Валидация определяет целостность системы.", "Одной декларации недостаточно, чтобы система была валидной. Она валидна только тогда, когда выполнены определённые структурные условия."]],
            ["Что мы определяем", [["условия Structured Reality™", "валидность систем и их рабочие состояния", "канонический смысл (UCL™)", "интероперабельность систем", "системную логику, к которой применимы механизмы управления"]]],
            ["Почему это важно", ["Современные системы дают сбои не из-за нехватки технологий, а из-за нестабильного смысла и неопределённой структуры.", "ИИ интерпретирует непоследовательно. Системы конфликтуют между предметными областями. Решениям недостаёт структурного обоснования.", "Без определённого смысла системы не могут сохранять валидность."]],
            ["Роль методологического органа", ["OOF® — орган, который не осуществляет непосредственное исполнение.", "OOF® не эксплуатирует системы и не навязывает результаты.", "OOF® определяет структурные условия, при которых системы сохраняют согласованность, интероперабельность и валидность."]],
            ["ИИ и целостность систем", ["ИИ не определяет смысл. ИИ работает на основе определённого смысла.", "В рамках OOF® интерпретация ограничена, смысл каноничен, а результаты поддаются структурной проверке."]],
            ["Global AI Incident Intelligence™", ["Реальные инциденты с ИИ непрерывно подвергают архитектуры управления стресс-тестированию.", "Отслеживайте возникающие инциденты, изучайте их последствия для управления и определяйте, какие архитектуры, стандарты и модули OOF® регулируют затронутую операционную реальность."]],
            ["Обзор", ["Structured Reality™ · Стандарты · Использование и валидность · Совместимость с OOF® · О методологическом органе"]],
            ["Заключительное заявление", ["OOF® не стремится к консенсусу. OOF® определяет структуру."]],
        ],
        "incident_link": "Открыть AI Incident Intelligence →",
    },
    "ko": {
        "description": "OOF® — OriginOpen® Foundation과 그 방법론 기반 체계를 소개하는 한국어 안내 페이지입니다.",
        "notice_title": "한국어 안내",
        "notice": "이 페이지는 OOF®의 공개 설명을 한국어로 제공합니다. 정본 방법론, 보호 대상 용어, 아키텍처 이름, 표준, 모듈 및 식별자는 영어 원문 그대로 유지됩니다.",
        "canonical": "영어 정본 보기",
        "hero": "OOF®는 시스템이 유효하고 상호 운용 가능하며 현실에 부합하기 위한 구조적 조건을 정의합니다.",
        "tagline": "AI, 시스템 및 거버넌스를 위한 Structured Reality™ 표준.",
        "validity": "시스템은 정의된 구조적 조건이 충족될 때에만 유효합니다.",
        "sections": [
            ["OOF® 소개", ["OOF® — OriginOpen® Foundation은 시스템 차원에서 활동하는 방법론적 기준 기관입니다.", "우리는 인간 시스템과 인공지능에서 의미, 구조 및 유효성이 어떻게 확립되는지를 정의합니다.", "이 플랫폼은 정본 참조 체계입니다. 시스템을 구현하지 않습니다. 시스템이 유효한 것으로 간주되는 조건을 정의합니다."]],
            ["시스템 모델", ["이용은 개방되어 있습니다. 호환성에는 조건이 따릅니다. 검증은 시스템의 무결성을 정의합니다.", "선언만으로 시스템이 유효해지는 것은 아닙니다. 정의된 구조적 조건이 충족될 때에만 유효합니다."]],
            ["정의하는 내용", [["Structured Reality™ 조건", "시스템의 유효성과 운영 상태", "정본으로 규정된 의미 (UCL™)", "시스템 간 상호 운용성", "거버넌스를 적용할 수 있는 시스템 논리"]]],
            ["중요한 이유", ["현대 시스템이 실패하는 이유는 기술 부족이 아니라 불안정한 의미와 정의되지 않은 구조에 있습니다.", "AI의 해석은 일관되지 않고, 시스템은 영역을 넘나들며 충돌하며, 의사결정에는 구조적 근거가 부족합니다.", "의미가 정의되어 있지 않으면 시스템은 유효성을 유지할 수 없습니다."]],
            ["기준 기관 모델", ["OOF®는 시스템을 직접 실행하지 않는 기준 기관입니다.", "OOF®는 시스템을 운영하거나 결과를 강제하지 않습니다.", "OOF®는 시스템이 일관성과 상호 운용성, 유효성을 유지하기 위한 구조적 조건을 정의합니다."]],
            ["AI와 시스템 무결성", ["AI는 의미를 정의하지 않습니다. AI는 정의된 의미를 바탕으로 작동합니다.", "OOF® 체계에서는 해석이 제한되고, 의미는 정본으로 규정되며, 출력은 구조적으로 검증할 수 있습니다."]],
            ["Global AI Incident Intelligence™", ["실제 AI 사고는 거버넌스 아키텍처에 대한 지속적인 스트레스 테스트가 됩니다.", "새롭게 발생하는 사고를 모니터링하고 거버넌스에 미치는 영향을 이해하며, 관련된 운영 현실에 어떤 OOF® 아키텍처, 표준 및 모듈이 적용되는지 확인하세요."]],
            ["둘러보기", ["Structured Reality™ · 표준 · 이용과 유효성 · OOF® 호환성 · 기준 기관 소개"]],
            ["마지막 선언", ["OOF®는 합의를 추구하지 않습니다. OOF®는 구조를 정의합니다."]],
        ],
        "incident_link": "AI Incident Intelligence 살펴보기 →",
    },
    "de": {
        "description": "Lokalisierte deutsche Zugangsebene zur OOF® — OriginOpen® Foundation und ihrer Methodologie-Infrastruktur.",
        "notice_title": "Lokalisierte Zugangsebene",
        "notice": "Diese Seite bietet einen deutschen Zugang zu den öffentlichen Erläuterungen von OOF®. Die kanonische Methodologie, geschützte Begriffe, Architekturnamen, Standards, Module und Kennungen bleiben in englischer Sprache unverändert.",
        "canonical": "Kanonische englische Fassung öffnen",
        "hero": "OOF® definiert die strukturellen Bedingungen, unter denen Systeme gültig, interoperabel und an der Realität ausgerichtet sind.",
        "tagline": "Structured Reality™ Standards für KI, Systeme und Governance.",
        "validity": "Ein System ist nur dann gültig, wenn definierte strukturelle Bedingungen erfüllt sind.",
        "sections": [
            ["Was dies ist", ["OOF® — OriginOpen® Foundation ist eine methodologische Referenzautorität, die auf Systemebene tätig ist.", "Wir definieren, wie Bedeutung, Struktur und Gültigkeit in menschlichen Systemen und in künstlicher Intelligenz begründet werden.", "Diese Plattform ist ein kanonisches Referenzsystem. Sie implementiert keine Systeme. Sie definiert die Bedingungen, unter denen Systeme als gültig gelten."]],
            ["Systemmodell", ["Die Nutzung ist offen. Die Kompatibilität ist bedingt. Validierung definiert die Systemintegrität.", "Ein System ist nicht aufgrund einer Erklärung gültig. Es ist nur dann gültig, wenn definierte strukturelle Bedingungen erfüllt sind."]],
            ["Was wir definieren", [["Structured Reality™ Bedingungen", "Systemgültigkeit und Betriebszustände", "kanonische Bedeutung (UCL™)", "Interoperabilität zwischen Systemen", "governance-fähige Systemlogik"]]],
            ["Warum es wichtig ist", ["Moderne Systeme scheitern nicht an fehlender Technologie, sondern an instabiler Bedeutung und undefinierter Struktur.", "KI interpretiert uneinheitlich. Systeme geraten domänenübergreifend in Konflikt. Entscheidungen fehlt eine strukturelle Grundlage.", "Ohne definierte Bedeutung können Systeme nicht gültig bleiben."]],
            ["Autoritätsmodell", ["OOF® ist eine nicht ausführende Autorität.", "OOF® betreibt keine Systeme und erzwingt keine Ergebnisse.", "OOF® definiert die strukturellen Bedingungen, unter denen Systeme kohärent, interoperabel und gültig bleiben."]],
            ["KI und Systemintegrität", ["KI definiert keine Bedeutung. KI arbeitet mit definierter Bedeutung.", "Innerhalb von OOF® ist die Interpretation begrenzt, die Bedeutung kanonisch und die Ausgabe strukturell überprüfbar."]],
            ["Global AI Incident Intelligence™", ["Reale KI-Vorfälle unterziehen Governance-Architekturen fortlaufend Belastungstests.", "Beobachten Sie neue Vorfälle, verstehen Sie deren Governance-Auswirkungen und erkennen Sie, welche OOF® Architekturen, Standards und Module die betroffene operative Realität regeln."]],
            ["Erkunden", ["Structured Reality™ · Standards · Nutzung und Gültigkeit · OOF® Kompatibilität · Über die Autorität"]],
            ["Abschlusserklärung", ["OOF® strebt keinen Konsens an. OOF® definiert Struktur."]],
        ],
        "incident_link": "AI Incident Intelligence erkunden →",
    },
    "zh-cn": {
        "description": "OOF® — OriginOpen® Foundation 及其方法论基础设施的简体中文公共访问层。",
        "notice_title": "本地化访问层",
        "notice": "本页面为 OOF® 的公共说明提供简体中文访问。规范性方法论、受保护术语、架构名称、标准、模块和标识符均保留英文原文，不作改动。",
        "canonical": "打开英文规范版本",
        "hero": "OOF® 定义系统保持有效、可互操作并与现实一致所需的结构条件。",
        "tagline": "面向人工智能、系统与治理的 Structured Reality™ 标准。",
        "validity": "只有满足明确规定的结构条件，系统才是有效的。",
        "sections": [
            ["这是什么", ["OOF® — OriginOpen® Foundation 是在系统层面运作的方法论参考权威。", "我们定义在人类系统和人工智能中建立意义、结构与有效性的方式。", "本平台是规范参考系统。它不实施系统，而是定义系统被视为有效所必须满足的条件。"]],
            ["系统模型", ["使用是开放的。兼容性是有条件的。验证界定系统完整性。", "系统不会因声明而有效。只有满足明确规定的结构条件，系统才是有效的。"]],
            ["我们定义什么", [["Structured Reality™ 条件", "系统有效性与运行状态", "规范意义（UCL™）", "系统之间的互操作性", "面向治理的系统逻辑"]]],
            ["为什么重要", ["现代系统的失败并非源于技术不足，而是源于意义不稳定和结构未定义。", "人工智能的解释可能不一致，系统会跨领域冲突，决策也可能缺少结构基础。", "没有明确的意义，系统就无法保持有效。"]],
            ["权威模型", ["OOF® 是非执行性权威。", "它不运行系统，也不强制产生结果。", "它定义系统保持一致、可互操作和有效所需的结构条件。"]],
            ["人工智能与系统完整性", ["人工智能不定义意义。人工智能基于已定义的意义运行。", "在 OOF® 中，解释受到约束，意义具有规范性，输出可在结构上得到验证。"]],
            ["Global AI Incident Intelligence™", ["现实世界中的人工智能事件持续对治理架构进行压力测试。", "监测新出现的事件，理解其治理影响，并查看哪些 OOF® 架构、标准和模块治理相关的运行现实。"]],
            ["探索", ["Structured Reality™ · 标准 · 使用与有效性 · OOF® 兼容性 · 关于权威"]],
            ["最终声明", ["OOF® 不寻求共识。OOF® 定义结构。"]],
        ],
        "incident_link": "探索 AI Incident Intelligence →",
    },
    "zh-hk": {
        "description": "OOF® — OriginOpen® Foundation 及其方法論基礎設施的繁體中文公共存取層。",
        "notice_title": "本地化存取層",
        "notice": "本頁面為 OOF® 的公共說明提供繁體中文存取。規範性方法論、受保護術語、架構名稱、標準、模組及識別碼均保留英文原文，不作改動。",
        "canonical": "開啟英文規範版本",
        "hero": "OOF® 定義系統保持有效、可互操作並與現實一致所需的結構條件。",
        "tagline": "面向人工智能、系統與治理的 Structured Reality™ 標準。",
        "validity": "只有符合明確界定的結構條件，系統才屬有效。",
        "sections": [
            ["這是甚麼", ["OOF® — OriginOpen® Foundation 是在系統層面運作的方法論參考權威。", "我們定義在人類系統及人工智能中建立意義、結構與有效性的方式。", "本平台是規範參考系統。它不實施系統，而是定義系統被視為有效所須符合的條件。"]],
            ["系統模型", ["使用是開放的。相容性是有條件的。驗證界定系統完整性。", "系統不會因聲明而有效。只有符合明確界定的結構條件，系統才屬有效。"]],
            ["我們定義甚麼", [["Structured Reality™ 條件", "系統有效性與運作狀態", "規範意義（UCL™）", "系統之間的互操作性", "面向治理的系統邏輯"]]],
            ["為何重要", ["現代系統失效並非源於技術不足，而是源於意義不穩定及結構未定義。", "人工智能的詮釋可能不一致，系統會跨領域衝突，決策亦可能缺乏結構基礎。", "沒有明確意義，系統便無法保持有效。"]],
            ["權威模型", ["OOF® 是非執行性權威。", "它不運作系統，亦不強制產生結果。", "它定義系統保持一致、可互操作及有效所需的結構條件。"]],
            ["人工智能與系統完整性", ["人工智能不定義意義。人工智能按已定義的意義運作。", "在 OOF® 中，詮釋受到約束，意義具有規範性，輸出可在結構上驗證。"]],
            ["Global AI Incident Intelligence™", ["現實世界的人工智能事故持續對治理架構進行壓力測試。", "監察新出現的事故、理解其治理影響，並查看哪些 OOF® 架構、標準及模組治理相關的運作現實。"]],
            ["探索", ["Structured Reality™ · 標準 · 使用與有效性 · OOF® 相容性 · 關於權威"]],
            ["最終聲明", ["OOF® 不尋求共識。OOF® 定義結構。"]],
        ],
        "incident_link": "探索 AI Incident Intelligence →",
    },
    "ja": {
        "description": "OOF® — OriginOpen® Foundation とその方法論インフラストラクチャへの日本語公開アクセス層です。",
        "notice_title": "ローカライズされたアクセス層",
        "notice": "このページは、OOF® の公開説明への日本語アクセスを提供します。規範的方法論、保護された用語、アーキテクチャ名、標準、モジュール、識別子は英語のまま変更されません。",
        "canonical": "正規の英語版を開く",
        "hero": "OOF® は、システムが有効で相互運用可能であり、現実と整合するための構造的条件を定義します。",
        "tagline": "AI、システム、ガバナンスのための Structured Reality™ 標準。",
        "validity": "定義された構造的条件を満たす場合にのみ、システムは有効です。",
        "sections": [
            ["OOF® とは", ["OOF® — OriginOpen® Foundation は、システムレベルで機能する方法論的参照機関です。", "人間のシステムと人工知能において、意味、構造、有効性がどのように確立されるかを定義します。", "このプラットフォームは正規の参照システムです。システムを実装するものではなく、システムが有効とみなされる条件を定義します。"]],
            ["システムモデル", ["利用は開かれています。互換性には条件があります。検証がシステムの完全性を定義します。", "宣言だけでシステムが有効になることはありません。定義された構造的条件を満たす場合にのみ有効です。"]],
            ["定義するもの", [["Structured Reality™ の条件", "システムの有効性と運用状態", "正規の意味（UCL™）", "システム間の相互運用性", "ガバナンスに対応したシステムロジック"]]],
            ["重要である理由", ["現代のシステムが失敗するのは、技術の不足ではなく、意味が不安定で構造が未定義だからです。", "AI の解釈は一貫性を欠き、システムは領域を越えて競合し、意思決定は構造的根拠を失います。", "意味が定義されていなければ、システムは有効性を維持できません。"]],
            ["権威モデル", ["OOF® は非実行型の権威です。", "システムを運用せず、結果を強制しません。", "システムが一貫性、相互運用性、有効性を保つための構造的条件を定義します。"]],
            ["AI とシステムの完全性", ["AI は意味を定義しません。AI は定義された意味に基づいて動作します。", "OOF® では、解釈は制約され、意味は正規化され、出力は構造的に検証可能です。"]],
            ["Global AI Incident Intelligence™", ["現実世界の AI インシデントは、ガバナンス・アーキテクチャを継続的にストレステストします。", "新たなインシデントを監視し、ガバナンス上の影響を理解し、関連する運用現実をどの OOF® アーキテクチャ、標準、モジュールが統治するかを確認できます。"]],
            ["探索", ["Structured Reality™ · 標準 · 利用と有効性 · OOF® 互換性 · 権威について"]],
            ["最終声明", ["OOF® は合意を求めません。OOF® は構造を定義します。"]],
        ],
        "incident_link": "AI Incident Intelligence を見る →",
    },
    "es": {
        "description": "Capa pública de acceso en español a OOF® — OriginOpen® Foundation y su infraestructura metodológica.",
        "notice_title": "Capa de acceso localizada",
        "notice": "Esta página ofrece acceso en español a las explicaciones públicas de OOF®. La metodología canónica, los términos protegidos, los nombres de arquitecturas, los estándares, los módulos y los identificadores permanecen sin cambios en inglés.",
        "canonical": "Abrir la versión canónica en inglés",
        "hero": "OOF® define las condiciones estructurales bajo las cuales los sistemas son válidos, interoperables y están alineados con la realidad.",
        "tagline": "Estándares Structured Reality™ para IA, sistemas y gobernanza.",
        "validity": "Un sistema solo es válido cuando se cumplen las condiciones estructurales definidas.",
        "sections": [
            ["Qué es", ["OOF® — OriginOpen® Foundation es una autoridad metodológica de referencia que opera en el ámbito de los sistemas.", "Definimos cómo se establecen el significado, la estructura y la validez en los sistemas humanos y la inteligencia artificial.", "Esta plataforma es un sistema canónico de referencia. No implementa sistemas. Define las condiciones bajo las cuales se consideran válidos."]],
            ["Modelo del sistema", ["El uso es abierto. La compatibilidad es condicional. La validación define la integridad del sistema.", "Un sistema no es válido por declaración. Solo es válido cuando se cumplen las condiciones estructurales definidas."]],
            ["Qué definimos", [["condiciones de Structured Reality™", "validez del sistema y estados operativos", "significado canónico (UCL™)", "interoperabilidad entre sistemas", "lógica de sistemas preparada para la gobernanza"]]],
            ["Por qué importa", ["Los sistemas modernos no fallan por falta de tecnología, sino por un significado inestable y una estructura indefinida.", "La IA interpreta de forma incoherente, los sistemas entran en conflicto entre dominios y las decisiones carecen de fundamento estructural.", "Sin un significado definido, los sistemas no pueden mantener su validez."]],
            ["Modelo de autoridad", ["OOF® es una autoridad no ejecutora.", "No opera sistemas ni impone resultados.", "Define las condiciones estructurales bajo las cuales los sistemas siguen siendo coherentes, interoperables y válidos."]],
            ["IA e integridad del sistema", ["La IA no define el significado. La IA opera sobre un significado definido.", "Dentro de OOF®, la interpretación está restringida, el significado es canónico y los resultados son verificables estructuralmente."]],
            ["Global AI Incident Intelligence™", ["Los incidentes reales de IA someten continuamente a prueba las arquitecturas de gobernanza.", "Supervise incidentes emergentes, comprenda sus implicaciones de gobernanza y vea qué arquitecturas, estándares y módulos de OOF® gobiernan la realidad operativa implicada."]],
            ["Explorar", ["Structured Reality™ · Estándares · Uso y validez · Compatibilidad OOF® · Acerca de la autoridad"]],
            ["Declaración final", ["OOF® no busca el consenso. OOF® define la estructura."]],
        ],
        "incident_link": "Explorar AI Incident Intelligence →",
    },
    "pt": {
        "description": "Camada pública de acesso em português à OOF® — OriginOpen® Foundation e à sua infraestrutura metodológica.",
        "notice_title": "Camada de acesso localizada",
        "notice": "Esta página disponibiliza acesso em português às explicações públicas da OOF®. A metodologia canónica, os termos protegidos, os nomes das arquiteturas, as normas, os módulos e os identificadores permanecem inalterados em inglês.",
        "canonical": "Abrir a versão canónica em inglês",
        "hero": "A OOF® define as condições estruturais segundo as quais os sistemas são válidos, interoperáveis e alinhados com a realidade.",
        "tagline": "Normas Structured Reality™ para IA, sistemas e governação.",
        "validity": "Um sistema só é válido quando são cumpridas as condições estruturais definidas.",
        "sections": [
            ["O que é", ["A OOF® — OriginOpen® Foundation é uma autoridade metodológica de referência que opera ao nível dos sistemas.", "Definimos como o significado, a estrutura e a validade são estabelecidos nos sistemas humanos e na inteligência artificial.", "Esta plataforma é um sistema canónico de referência. Não implementa sistemas. Define as condições em que os sistemas são considerados válidos."]],
            ["Modelo do sistema", ["A utilização é aberta. A compatibilidade é condicional. A validação define a integridade do sistema.", "Um sistema não é válido por declaração. Só é válido quando são cumpridas as condições estruturais definidas."]],
            ["O que definimos", [["condições de Structured Reality™", "validade do sistema e estados operacionais", "significado canónico (UCL™)", "interoperabilidade entre sistemas", "lógica de sistemas preparada para governação"]]],
            ["Porque é importante", ["Os sistemas modernos não falham por falta de tecnologia, mas devido a significado instável e estrutura indefinida.", "A IA interpreta de forma inconsistente, os sistemas entram em conflito entre domínios e as decisões carecem de fundamento estrutural.", "Sem significado definido, os sistemas não podem permanecer válidos."]],
            ["Modelo de autoridade", ["A OOF® é uma autoridade não executora.", "Não opera sistemas nem impõe resultados.", "Define as condições estruturais em que os sistemas permanecem coerentes, interoperáveis e válidos."]],
            ["IA e integridade do sistema", ["A IA não define significado. A IA opera sobre significado definido.", "Na OOF®, a interpretação é limitada, o significado é canónico e os resultados são estruturalmente verificáveis."]],
            ["Global AI Incident Intelligence™", ["Os incidentes reais de IA submetem continuamente as arquiteturas de governação a testes de esforço.", "Acompanhe incidentes emergentes, compreenda as suas implicações de governação e veja que arquiteturas, normas e módulos da OOF® governam a realidade operacional envolvida."]],
            ["Explorar", ["Structured Reality™ · Normas · Utilização e validade · Compatibilidade OOF® · Sobre a autoridade"]],
            ["Declaração final", ["A OOF® não procura consenso. A OOF® define estrutura."]],
        ],
        "incident_link": "Explorar AI Incident Intelligence →",
    },
    "fr": {
        "description": "Couche d’accès public en français à OOF® — OriginOpen® Foundation et à son infrastructure méthodologique.",
        "notice_title": "Couche d’accès localisée",
        "notice": "Cette page donne accès en français aux explications publiques d’OOF®. La méthodologie canonique, les termes protégés, les noms d’architectures, les standards, les modules et les identifiants demeurent inchangés en anglais.",
        "canonical": "Ouvrir la version canonique en anglais",
        "hero": "OOF® définit les conditions structurelles dans lesquelles les systèmes sont valides, interopérables et alignés sur la réalité.",
        "tagline": "Standards Structured Reality™ pour l’IA, les systèmes et la gouvernance.",
        "validity": "Un système n’est valide que lorsque les conditions structurelles définies sont satisfaites.",
        "sections": [
            ["Ce que c’est", ["OOF® — OriginOpen® Foundation est une autorité méthodologique de référence qui intervient au niveau des systèmes.", "Nous définissons la manière dont le sens, la structure et la validité sont établis dans les systèmes humains et l’intelligence artificielle.", "Cette plateforme est un système de référence canonique. Elle ne met pas en œuvre les systèmes. Elle définit les conditions dans lesquelles ils sont considérés comme valides."]],
            ["Modèle du système", ["L’utilisation est ouverte. La compatibilité est conditionnelle. La validation définit l’intégrité du système.", "Un système n’est pas valide par simple déclaration. Il ne l’est que lorsque les conditions structurelles définies sont satisfaites."]],
            ["Ce que nous définissons", [["les conditions Structured Reality™", "la validité des systèmes et leurs états opérationnels", "le sens canonique (UCL™)", "l’interopérabilité entre les systèmes", "la logique des systèmes adaptée à la gouvernance"]]],
            ["Pourquoi cela compte", ["Les systèmes modernes échouent non par manque de technologie, mais en raison d’un sens instable et d’une structure non définie.", "L’IA interprète de manière incohérente, les systèmes entrent en conflit entre les domaines et les décisions manquent de fondement structurel.", "Sans sens défini, les systèmes ne peuvent pas rester valides."]],
            ["Modèle d’autorité", ["OOF® est une autorité non exécutante.", "Elle n’exploite pas les systèmes et n’impose pas les résultats.", "Elle définit les conditions structurelles dans lesquelles les systèmes restent cohérents, interopérables et valides."]],
            ["IA et intégrité des systèmes", ["L’IA ne définit pas le sens. Elle fonctionne à partir d’un sens défini.", "Au sein d’OOF®, l’interprétation est encadrée, le sens est canonique et les résultats sont vérifiables sur le plan structurel."]],
            ["Global AI Incident Intelligence™", ["Les incidents réels liés à l’IA soumettent en permanence les architectures de gouvernance à des tests de résistance.", "Suivez les incidents émergents, comprenez leurs implications en matière de gouvernance et identifiez les architectures, standards et modules OOF® qui gouvernent la réalité opérationnelle concernée."]],
            ["Explorer", ["Structured Reality™ · Standards · Utilisation et validité · Compatibilité OOF® · À propos de l’autorité"]],
            ["Déclaration finale", ["OOF® ne recherche pas le consensus. OOF® définit la structure."]],
        ],
        "incident_link": "Explorer AI Incident Intelligence →",
    },
    "hi": {
        "description": "OOF® — OriginOpen® Foundation और उसकी कार्यप्रणाली अवसंरचना के लिए हिन्दी सार्वजनिक पहुँच-स्तर।",
        "notice_title": "स्थानीयकृत पहुँच-स्तर",
        "notice": "यह पृष्ठ OOF® की सार्वजनिक व्याख्याओं तक हिन्दी में पहुँच देता है। प्रामाणिक कार्यप्रणाली, संरक्षित शब्द, आर्किटेक्चर के नाम, मानकों और मॉड्यूलों के प्रामाणिक नाम तथा पहचानकर्ता अंग्रेज़ी में अपरिवर्तित रहते हैं।",
        "canonical": "प्रामाणिक अंग्रेज़ी संस्करण खोलें",
        "hero": "OOF® उन संरचनात्मक शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियाँ वैध, परस्पर-संचालनीय और वास्तविकता के अनुरूप होती हैं।",
        "tagline": "कृत्रिम बुद्धिमत्ता, प्रणालियों और अभिशासन के लिए Structured Reality™ मानक।",
        "validity": "कोई प्रणाली तभी वैध होती है जब निर्धारित संरचनात्मक शर्तें पूरी हों।",
        "sections": [
            ["यह क्या है", ["OOF® — OriginOpen® Foundation एक कार्यप्रणाली संदर्भ प्राधिकरण है जो प्रणाली-स्तर पर कार्य करता है।", "हम परिभाषित करते हैं कि मानव प्रणालियों और कृत्रिम बुद्धिमत्ता में अर्थ, संरचना और वैधता कैसे स्थापित होती है।", "यह मंच एक प्रामाणिक संदर्भ प्रणाली है। यह प्रणालियों को लागू नहीं करता। यह उन शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियों को वैध माना जाता है।"]],
            ["प्रणाली मॉडल", ["उपयोग खुला है। संगतता सशर्त है। सत्यापन प्रणाली की अखंडता को परिभाषित करता है।", "घोषणा मात्र से कोई प्रणाली वैध नहीं होती। वह तभी वैध होती है जब निर्धारित संरचनात्मक शर्तें पूरी हों।"]],
            ["हम क्या परिभाषित करते हैं", [["Structured Reality™ की शर्तें", "प्रणाली की वैधता और परिचालन अवस्थाएँ", "प्रामाणिक अर्थ (UCL™)", "प्रणालियों के बीच परस्पर-संचालनीयता", "अभिशासन के लिए तैयार प्रणाली-तर्क"]]],
            ["यह क्यों महत्वपूर्ण है", ["आधुनिक प्रणालियाँ प्रौद्योगिकी की कमी से नहीं, बल्कि अस्थिर अर्थ और अपरिभाषित संरचना के कारण विफल होती हैं।", "AI असंगत रूप से व्याख्या करता है, प्रणालियाँ अलग-अलग क्षेत्रों में टकराती हैं और निर्णयों में संरचनात्मक आधार का अभाव होता है।", "परिभाषित अर्थ के बिना प्रणालियाँ वैध नहीं रह सकतीं।"]],
            ["प्राधिकरण मॉडल", ["OOF® एक गैर-निष्पादक प्राधिकरण है।", "यह प्रणालियों को संचालित नहीं करता और परिणाम लागू नहीं करता।", "यह उन संरचनात्मक शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियाँ सुसंगत, परस्पर-संचालनीय और वैध रहती हैं।"]],
            ["AI और प्रणाली की अखंडता", ["AI अर्थ को परिभाषित नहीं करता। AI परिभाषित अर्थ पर कार्य करता है।", "OOF® के भीतर व्याख्या सीमित है, अर्थ प्रामाणिक है और परिणाम संरचनात्मक रूप से सत्यापित किए जा सकते हैं।"]],
            ["Global AI Incident Intelligence™", ["वास्तविक दुनिया की कृत्रिम बुद्धिमत्ता संबंधी घटनाएँ अभिशासन आर्किटेक्चर का निरंतर तनाव-परीक्षण करती हैं।", "उभरती घटनाओं की निगरानी करें, उनके अभिशासन संबंधी प्रभावों को समझें और देखें कि कौन-से OOF® आर्किटेक्चर, मानक और मॉड्यूल संबंधित परिचालन वास्तविकता को अभिशासित करते हैं।"]],
            ["अन्वेषण", ["Structured Reality™ · मानक · उपयोग और वैधता · OOF® संगतता · प्राधिकरण के बारे में"]],
            ["अंतिम वक्तव्य", ["OOF® सहमति नहीं खोजता। OOF® संरचना को परिभाषित करता है।"]],
        ],
        "incident_link": "AI Incident Intelligence देखें →",
    },
}


def localized_text(value: str, rtl: bool = False) -> str:
    escaped = html.escape(value)
    if rtl:
        terms = ["OOF® — OriginOpen® Foundation", "Global AI Incident Intelligence™", "AI Incident Intelligence", "Structured Reality™", "OOF®", "UCL™"]
        pattern = "|".join(re.escape(html.escape(term)) for term in terms)
        escaped = re.sub(pattern, lambda match: '<bdi dir="ltr">' + match.group(0) + '</bdi>', escaped)
    return escaped


def render_blocks(blocks: list[str | list[str]], rtl: bool = False) -> str:
    rendered = []
    for block in blocks:
        if isinstance(block, list):
            rendered.append("<ul>" + "".join(f"<li>{localized_text(item, rtl)}</li>" for item in block) + "</ul>")
        else:
            rendered.append(f"<p>{localized_text(block, rtl)}</p>")
    return "\n".join(rendered)


def render_page(prefix: str, details: dict[str, str], translation: dict) -> str:
    sections = []
    for heading, blocks in translation["sections"]:
        extra = ""
        if heading == "Global AI Incident Intelligence™":
            extra = f'<p><a href="../ai-incidents/"><strong>{localized_text(translation["incident_link"], prefix == "ar")}</strong></a></p>'
        sections.append(
            '<section class="container"><div class="oof-warning3">'
            f'<h2>{localized_text(heading, prefix == "ar")}</h2>{render_blocks(blocks, prefix == "ar")}{extra}'
            '</div><section class="viewbor"></section></section>'
        )
    title = f'OOF® — OriginOpen® Foundation | {details["native"]}'
    return f'''<!doctype html>
<html lang="{details["code"]}"{' dir="rtl"' if prefix == 'ar' else ''}>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <link rel="icon" href="../favicon.ico" sizes="any" />
  <link rel="stylesheet" href="../style.css" />
</head>
<body>
<div id="header"></div>
  <section class="container">
    <div class="oof-localization-notice">
      <p><strong>{localized_text(translation["notice_title"], prefix == "ar")}</strong></p>
      <p>{localized_text(translation["notice"], prefix == "ar")}</p>
      <p><a href="../index.html" hreflang="en">{localized_text(translation["canonical"], prefix == "ar")}</a></p>
    </div>
    <h1>{localized_text(translation["hero"], prefix == "ar")}</h1>
    <div class="oof-warning3">
      <p>{localized_text(translation["tagline"], prefix == "ar")}</p>
      <p>{localized_text(translation["validity"], prefix == "ar")}</p>
    </div>
    <section class="viewbor"></section>
  </section>
  {''.join(sections)}
<div id="footer"></div>
<script src="../header.js"></script>
<script>
Promise.all([
  fetch("../header.html").then(response => response.text()),
  fetch("../footer.html").then(response => response.text())
]).then(([header, footer]) => {{
  document.getElementById("header").innerHTML = header;
  document.getElementById("footer").innerHTML = footer;
  if (window.normalizePageLinks) window.normalizePageLinks();
}});
</script>
</body>
</html>
'''


def write_policy() -> None:
    policy_dir = ROOT / "data" / "localization"
    policy_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0",
        "canonicalMethodologyLanguage": "en",
        "principle": "ONE CANONICAL METHODOLOGY. MULTIPLE LANGUAGES OF ACCESS. NO METHODOLOGICAL DRIFT.",
        "languages": [{"prefix": prefix, **details} for prefix, details in LANGUAGES.items()],
        "translatedPublicPages": ["index.html"],
        "canonicalEnglishOnly": [
            "Parent Standards and their normative content",
            "Core Modules and their normative content",
            "canonical Standard and Module names",
            "Origin IDs, architecture acronyms, trademarks, protected terms and formal identifiers",
        ],
        "fallback": "When a reviewed localized page is unavailable, retain and link to the canonical English page.",
    }
    (policy_dir / "localization-policy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    for prefix, details in LANGUAGES.items():
        output_dir = ROOT / prefix
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "index.html").write_text(
            render_page(prefix, details, TRANSLATIONS[prefix]), encoding="utf-8", newline="\n"
        )
    write_policy()
    print(f"Built {len(LANGUAGES)} reviewed public-language access layers.")


if __name__ == "__main__":
    main()
