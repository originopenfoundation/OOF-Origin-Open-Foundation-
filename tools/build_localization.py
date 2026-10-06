#!/usr/bin/env python3
"""Build reviewed public-language access layers without translating normative OOF material."""

from __future__ import annotations

import html
import json
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
    "hi": {"code": "hi-IN", "native": "हिन्दी", "english": "Hindi"},
}

TRANSLATIONS = {
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
        "tagline": "AI、システム、ガバナンスのための Structured Reality™ Standards。",
        "validity": "定義された構造的条件を満たす場合にのみ、システムは有効です。",
        "sections": [
            ["OOF® とは", ["OOF® — OriginOpen® Foundation は、システムレベルで機能する方法論的参照機関です。", "人間のシステムと人工知能において、意味、構造、有効性がどのように確立されるかを定義します。", "このプラットフォームは正規の参照システムです。システムを実装するものではなく、システムが有効とみなされる条件を定義します。"]],
            ["システムモデル", ["利用は開かれています。互換性には条件があります。検証がシステムの完全性を定義します。", "宣言だけでシステムが有効になることはありません。定義された構造的条件を満たす場合にのみ有効です。"]],
            ["定義するもの", [["Structured Reality™ の条件", "システムの有効性と運用状態", "正規の意味（UCL™）", "システム間の相互運用性", "ガバナンスに対応したシステムロジック"]]],
            ["重要である理由", ["現代のシステムが失敗するのは、技術の不足ではなく、意味が不安定で構造が未定義だからです。", "AI の解釈は一貫性を欠き、システムは領域を越えて競合し、意思決定は構造的根拠を失います。", "意味が定義されていなければ、システムは有効性を維持できません。"]],
            ["権威モデル", ["OOF® は非実行型の権威です。", "システムを運用せず、結果を強制しません。", "システムが一貫性、相互運用性、有効性を保つための構造的条件を定義します。"]],
            ["AI とシステムの完全性", ["AI は意味を定義しません。AI は定義された意味に基づいて動作します。", "OOF® では、解釈は制約され、意味は正規化され、出力は構造的に検証可能です。"]],
            ["Global AI Incident Intelligence™", ["現実世界の AI インシデントは、ガバナンス・アーキテクチャを継続的にストレステストします。", "新たなインシデントを監視し、ガバナンス上の影響を理解し、関連する運用現実をどの OOF® アーキテクチャ、標準、モジュールが統治するかを確認できます。"]],
            ["探索", ["Structured Reality™ · Standards · 利用と有効性 · OOF® Compatibility · 権威について"]],
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
            ["Modelo de autoridad", ["OOF® es una autoridad no ejecutiva.", "No opera sistemas ni impone resultados.", "Define las condiciones estructurales bajo las cuales los sistemas siguen siendo coherentes, interoperables y válidos."]],
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
            ["Modelo de autoridade", ["A OOF® é uma autoridade não executiva.", "Não opera sistemas nem impõe resultados.", "Define as condições estruturais em que os sistemas permanecem coerentes, interoperáveis e válidos."]],
            ["IA e integridade do sistema", ["A IA não define significado. A IA opera sobre significado definido.", "Na OOF®, a interpretação é limitada, o significado é canónico e os resultados são estruturalmente verificáveis."]],
            ["Global AI Incident Intelligence™", ["Os incidentes reais de IA submetem continuamente as arquiteturas de governação a testes de esforço.", "Acompanhe incidentes emergentes, compreenda as suas implicações de governação e veja que arquiteturas, normas e módulos da OOF® governam a realidade operacional envolvida."]],
            ["Explorar", ["Structured Reality™ · Normas · Utilização e validade · Compatibilidade OOF® · Sobre a autoridade"]],
            ["Declaração final", ["A OOF® não procura consenso. A OOF® define estrutura."]],
        ],
        "incident_link": "Explorar AI Incident Intelligence →",
    },
    "hi": {
        "description": "OOF® — OriginOpen® Foundation और उसकी कार्यप्रणाली अवसंरचना के लिए हिन्दी सार्वजनिक पहुँच-स्तर।",
        "notice_title": "स्थानीयकृत पहुँच-स्तर",
        "notice": "यह पृष्ठ OOF® की सार्वजनिक व्याख्याओं तक हिन्दी में पहुँच देता है। प्रामाणिक कार्यप्रणाली, संरक्षित शब्द, आर्किटेक्चर के नाम, Standards, Modules और identifiers अंग्रेज़ी में अपरिवर्तित रहते हैं।",
        "canonical": "प्रामाणिक अंग्रेज़ी संस्करण खोलें",
        "hero": "OOF® उन संरचनात्मक शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियाँ वैध, परस्पर-संचालनीय और वास्तविकता के अनुरूप होती हैं।",
        "tagline": "AI, प्रणालियों और governance के लिए Structured Reality™ Standards।",
        "validity": "कोई प्रणाली तभी वैध होती है जब निर्धारित संरचनात्मक शर्तें पूरी हों।",
        "sections": [
            ["यह क्या है", ["OOF® — OriginOpen® Foundation एक कार्यप्रणाली संदर्भ प्राधिकरण है जो प्रणाली-स्तर पर कार्य करता है।", "हम परिभाषित करते हैं कि मानव प्रणालियों और कृत्रिम बुद्धिमत्ता में अर्थ, संरचना और वैधता कैसे स्थापित होती है।", "यह मंच एक प्रामाणिक संदर्भ प्रणाली है। यह प्रणालियों को लागू नहीं करता। यह उन शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियों को वैध माना जाता है।"]],
            ["प्रणाली मॉडल", ["उपयोग खुला है। संगतता सशर्त है। Validation प्रणाली की अखंडता को परिभाषित करता है।", "घोषणा मात्र से कोई प्रणाली वैध नहीं होती। वह तभी वैध होती है जब निर्धारित संरचनात्मक शर्तें पूरी हों।"]],
            ["हम क्या परिभाषित करते हैं", [["Structured Reality™ की शर्तें", "प्रणाली की वैधता और परिचालन अवस्थाएँ", "प्रामाणिक अर्थ (UCL™)", "प्रणालियों के बीच परस्पर-संचालनीयता", "governance के लिए तैयार प्रणाली-तर्क"]]],
            ["यह क्यों महत्वपूर्ण है", ["आधुनिक प्रणालियाँ प्रौद्योगिकी की कमी से नहीं, बल्कि अस्थिर अर्थ और अपरिभाषित संरचना के कारण विफल होती हैं।", "AI असंगत रूप से व्याख्या करता है, प्रणालियाँ अलग-अलग क्षेत्रों में टकराती हैं और निर्णयों में संरचनात्मक आधार का अभाव होता है।", "परिभाषित अर्थ के बिना प्रणालियाँ वैध नहीं रह सकतीं।"]],
            ["प्राधिकरण मॉडल", ["OOF® एक गैर-निष्पादक प्राधिकरण है।", "यह प्रणालियों को संचालित नहीं करता और परिणाम लागू नहीं करता।", "यह उन संरचनात्मक शर्तों को परिभाषित करता है जिनके अंतर्गत प्रणालियाँ सुसंगत, परस्पर-संचालनीय और वैध रहती हैं।"]],
            ["AI और प्रणाली की अखंडता", ["AI अर्थ को परिभाषित नहीं करता। AI परिभाषित अर्थ पर कार्य करता है।", "OOF® के भीतर व्याख्या सीमित है, अर्थ प्रामाणिक है और परिणाम संरचनात्मक रूप से सत्यापित किए जा सकते हैं।"]],
            ["Global AI Incident Intelligence™", ["वास्तविक दुनिया की AI घटनाएँ governance architectures की निरंतर stress-testing करती हैं।", "उभरती घटनाओं की निगरानी करें, उनके governance प्रभावों को समझें और देखें कि कौन-से OOF® architectures, Standards और Modules संबंधित परिचालन वास्तविकता को govern करते हैं।"]],
            ["अन्वेषण", ["Structured Reality™ · Standards · उपयोग और वैधता · OOF® Compatibility · प्राधिकरण के बारे में"]],
            ["अंतिम वक्तव्य", ["OOF® सहमति नहीं खोजता। OOF® संरचना को परिभाषित करता है।"]],
        ],
        "incident_link": "AI Incident Intelligence देखें →",
    },
}


def render_blocks(blocks: list[str | list[str]]) -> str:
    rendered = []
    for block in blocks:
        if isinstance(block, list):
            rendered.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in block) + "</ul>")
        else:
            rendered.append(f"<p>{html.escape(block)}</p>")
    return "\n".join(rendered)


def render_page(prefix: str, details: dict[str, str], translation: dict) -> str:
    sections = []
    for heading, blocks in translation["sections"]:
        extra = ""
        if heading == "Global AI Incident Intelligence™":
            extra = f'<p><a href="../ai-incidents/"><strong>{html.escape(translation["incident_link"])}</strong></a></p>'
        sections.append(
            '<section class="container"><div class="oof-warning3">'
            f'<h2>{html.escape(heading)}</h2>{render_blocks(blocks)}{extra}'
            '</div><section class="viewbor"></section></section>'
        )
    title = f'OOF® — OriginOpen® Foundation | {details["native"]}'
    return f'''<!doctype html>
<html lang="{details["code"]}">
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
      <p><strong>{html.escape(translation["notice_title"])}</strong></p>
      <p>{html.escape(translation["notice"])}</p>
      <p><a href="../index.html" hreflang="en">{html.escape(translation["canonical"])}</a></p>
    </div>
    <h1>{html.escape(translation["hero"])}</h1>
    <div class="oof-warning3">
      <p>{html.escape(translation["tagline"])}</p>
      <p>{html.escape(translation["validity"])}</p>
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
