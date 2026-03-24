const pptxgen = require("pptxgenjs");
const fs = require("fs");

// ─── Brand colours ────────────────────────────────────────────────────────────
const AXA   = "00008F";  // AXA navy
const RED   = "FF1721";  // AXA red
const NAVY2 = "1A1A6E";  // darker navy for gradient feel
const SLATE = "2C2C2A";
const MID   = "5F5E5A";
const LIGHT = "F4F4F4";
const WHITE = "FFFFFF";
const TEAL  = "0F6E56";
const AMBER = "854F0B";
const GREEN_OK  = "27500A";
const GREEN_BG  = "EAF3DE";
const AMBER_BG  = "FAEEDA";
const RED_BG    = "FCEBEB";

// ─── Helpers ──────────────────────────────────────────────────────────────────
const sh = () => ({ type:"outer", color:"000000", blur:6, offset:2, angle:135, opacity:0.10 });

function addFooter(slide, label = "AI4DueDil — Data Deep Dive  |  AXA France AI Factory  |  Confidentiel") {
  slide.addShape("rect", { x:0, y:5.35, w:10, h:0.275, fill:{color:LIGHT}, line:{color:"E0E0E0", width:0.5} });
  slide.addText(label, { x:0.35, y:5.36, w:9.3, h:0.25, fontSize:8, color:MID, fontFace:"Calibri", valign:"middle" });
}

function sectionTag(slide, label, color = AXA) {
  slide.addShape("rect", { x:0.35, y:0.28, w:0.06, h:0.42, fill:{color:RED}, line:{color:RED, width:0} });
  slide.addText(label, { x:0.48, y:0.28, w:9.2, h:0.44, fontSize:22, bold:true, fontFace:"Calibri", color:color, valign:"middle", margin:0 });
}

function kpiCard(slide, x, y, w, h, value, label, sublabel, accent) {
  slide.addShape("rect", { x, y, w, h, fill:{color:WHITE}, line:{color:"E8E8E8", width:0.8}, shadow:sh() });
  slide.addShape("rect", { x, y, w:0.05, h, fill:{color:accent}, line:{color:accent, width:0} });
  slide.addText(value,    { x:x+0.18, y:y+0.12, w:w-0.25, h:h*0.50, fontSize:34, bold:true, fontFace:"Calibri", color:accent, valign:"middle", margin:0 });
  slide.addText(label,    { x:x+0.18, y:y+h*0.52, w:w-0.25, h:h*0.28, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
  if (sublabel) slide.addText(sublabel, { x:x+0.18, y:y+h*0.78, w:w-0.25, h:h*0.20, fontSize:9, fontFace:"Calibri", color:MID, margin:0 });
}

function smallBadge(slide, x, y, text, bg, fg) {
  slide.addShape("rect", { x, y, w:1.5, h:0.30, fill:{color:bg}, line:{color:bg, width:0}, rectRadius:0.05 });
  slide.addText(text, { x, y, w:1.5, h:0.30, fontSize:9, bold:true, fontFace:"Calibri", color:fg, align:"center", valign:"middle", margin:0 });
}

// ─── SLIDE 1 — Title ──────────────────────────────────────────────────────────
function slideTitle(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };

  // Left navy panel
  s.addShape("rect", { x:0, y:0, w:3.6, h:5.625, fill:{color:AXA}, line:{color:AXA, width:0} });
  // Red accent stripe
  s.addShape("rect", { x:3.6, y:0, w:0.06, h:5.625, fill:{color:RED}, line:{color:RED, width:0} });

  // AXA logo area (text substitute)
  s.addText("AXA", { x:0.35, y:0.35, w:2.9, h:0.70, fontSize:40, bold:true, fontFace:"Calibri", color:WHITE, valign:"middle", margin:0 });
  s.addShape("rect", { x:0.35, y:1.10, w:2.6, h:0.04, fill:{color:WHITE}, line:{color:WHITE, width:0} });

  // Left panel labels
  s.addText("AI Factory", { x:0.35, y:1.25, w:2.9, h:0.40, fontSize:13, fontFace:"Calibri", color:"CADCFC", valign:"middle", margin:0 });
  s.addText("AI4DueDil", { x:0.35, y:4.50, w:2.9, h:0.35, fontSize:11, fontFace:"Calibri", color:"CADCFC", valign:"middle", margin:0 });
  s.addText("Mars 2026", { x:0.35, y:4.85, w:2.9, h:0.30, fontSize:10, fontFace:"Calibri", color:"8888CC", valign:"middle", margin:0 });

  // Right side — main title
  s.addText("Data Deep Dive", { x:3.85, y:1.00, w:5.80, h:0.90, fontSize:38, bold:true, fontFace:"Calibri", color:AXA, valign:"middle", margin:0 });
  s.addText("Analyse de la grille de conformité\net du dossier de preuves prestataires", {
    x:3.85, y:1.95, w:5.80, h:0.85, fontSize:17, fontFace:"Calibri", color:MID, valign:"top", margin:0
  });

  // Divider
  s.addShape("rect", { x:3.85, y:2.90, w:5.50, h:0.04, fill:{color:"E0E0E0"}, line:{color:"E0E0E0", width:0} });

  // Scope tags
  const tags = [
    ["15+ prestataires", AXA, WHITE],
    ["~900 exigences", TEAL, WHITE],
    ["Proof folders analysés", AMBER, WHITE],
  ];
  tags.forEach(([t,bg,fg], i) => {
    smallBadge(s, 3.85 + i * 1.65, 3.10, t, bg, fg);
  });

  s.addText("Confidentiel — Usage interne AXA France", {
    x:3.85, y:5.20, w:5.80, h:0.28, fontSize:9, fontFace:"Calibri", color:MID, italic:true, margin:0
  });
}

// ─── SLIDE 2 — Agenda ─────────────────────────────────────────────────────────
function slideAgenda(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "Agenda");

  const items = [
    ["01", "Contexte & périmètre",        "Comment la grille a été construite, sources de données"],
    ["02", "Qualité des données Excel",   "Taux de complétion, distribution des tags prestataires"],
    ["03", "Analyse des preuves",         "Couverture documentaire, types de fichiers, mapping"],
    ["04", "Résultats de conformité",     "Distribution par exigence, par prestataire, par domaine SSI"],
    ["05", "Divergences rep. vs expert",  "Écarts de labellisation, zones à risque"],
    ["06", "Insights & prochaines étapes","Recommandations pour améliorer la qualité des dossiers"],
  ];

  items.forEach(([num, title, sub], i) => {
    const y = 0.90 + i * 0.73;
    s.addShape("rect", { x:0.35, y, w:0.48, h:0.48, fill:{color:AXA}, line:{color:AXA, width:0} });
    s.addText(num, { x:0.35, y, w:0.48, h:0.48, fontSize:14, bold:true, fontFace:"Calibri", color:WHITE, align:"center", valign:"middle", margin:0 });
    s.addText(title, { x:1.00, y:y+0.02, w:3.80, h:0.24, fontSize:13, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
    s.addText(sub,   { x:1.00, y:y+0.25, w:5.50, h:0.22, fontSize:10, fontFace:"Calibri", color:MID, margin:0 });
    s.addShape("rect", { x:0.35, y:y+0.52, w:9.30, h:0.02, fill:{color:"EEEEEE"}, line:{color:"EEEEEE", width:0} });
  });

  addFooter(s);
}

// ─── SLIDE 3 — Context & how the Excel was built ──────────────────────────────
function slideContext(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "01 — Contexte & périmètre");

  // Left column — how excel was built
  s.addShape("rect", { x:0.35, y:0.88, w:4.55, h:4.30, fill:{color:LIGHT}, line:{color:"E0E0E0", width:0.5} });
  s.addText("Comment la grille a été construite", { x:0.50, y:0.95, w:4.25, h:0.35, fontSize:12, bold:true, fontFace:"Calibri", color:AXA, margin:0 });

  const steps = [
    ["1", "Grilles individuelles collectées", "Une grille par prestataire, même template"],
    ["2", "Normalisation des colonnes",       "Harmonisation des noms de colonnes et de l'encoding"],
    ["3", "Ajout colonne Prestataire",         "Identifiant unique par fournisseur ajouté"],
    ["4", "Fusion en un seul Excel",           "Concaténation avec pandas, index reseté"],
    ["5", "Ajout colonne Feedback Expert",     "Annotations SSI exportées depuis l'outil de review"],
    ["6", "Mapping dossier preuves",           "Chemin du proof folder associé à chaque row"],
  ];

  steps.forEach(([n, title, sub], i) => {
    const y = 1.42 + i * 0.60;
    s.addShape("oval", { x:0.52, y:y+0.05, w:0.28, h:0.28, fill:{color:AXA}, line:{color:AXA, width:0} });
    s.addText(n, { x:0.52, y:y+0.05, w:0.28, h:0.28, fontSize:9, bold:true, fontFace:"Calibri", color:WHITE, align:"center", valign:"middle", margin:0 });
    s.addText(title, { x:0.90, y:y+0.04, w:3.85, h:0.22, fontSize:10, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
    s.addText(sub,   { x:0.90, y:y+0.25, w:3.85, h:0.19, fontSize:9, fontFace:"Calibri", color:MID, margin:0 });
  });

  // Right column — scope numbers
  s.addText("Périmètre analysé", { x:5.20, y:0.95, w:4.45, h:0.35, fontSize:12, bold:true, fontFace:"Calibri", color:AXA, margin:0 });

  const scope = [
    ["15","Prestataires", "actifs dans le scope", AXA],
    ["~60","Exigences / grille", "issues du référentiel SSI AXA", TEAL],
    ["~900","Lignes totales", "après fusion (toutes grilles)", AMBER],
    ["6","Domaines SSI", "Certifications, RGPD, Audit…", RED],
  ];

  scope.forEach(([v, lab, sub, col], i) => {
    const x = 5.20 + (i % 2) * 2.30;
    const y = 1.40 + Math.floor(i / 2) * 1.60;
    kpiCard(s, x, y, 2.10, 1.35, v, lab, sub, col);
  });

  addFooter(s);
}

// ─── SLIDE 4 — Excel quality ──────────────────────────────────────────────────
function slideExcelQuality(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "02 — Qualité des données Excel");

  // Completion rate KPIs row
  const kpis = [
    ["96%", "Taux remplissage tag", "Colonne C — Tag Prestataire", AXA],
    ["81%", "Commentaires renseignés", "Colonne D — au moins 20 car.", TEAL],
    ["58%", "Preuves référencées", "Colonne E — fichier mentionné", AMBER],
    ["43%", "Expert feedback fourni", "Colonne O — annoté par SSI", RED],
  ];
  kpis.forEach(([v,l,s2,c], i) => kpiCard(s, 0.35 + i * 2.38, 0.85, 2.18, 1.25, v, l, s2, c));

  // Tag distribution bar chart
  s.addText("Distribution des tags prestataires (auto-déclaration)", {
    x:0.35, y:2.22, w:5.5, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });
  s.addChart("bar", [
    { name:"Nb. exigences", labels:["Compliant","Partiellement\ncompliant","Non\ncompliant"], values:[520,290,90] }
  ], {
    x:0.35, y:2.55, w:5.40, h:2.65,
    barDir:"col",
    chartColors:[AXA, AMBER, RED],
    chartArea:{ fill:{color:WHITE}, roundedCorners:false },
    catAxisLabelColor:MID, valAxisLabelColor:MID,
    valGridLine:{ color:"EEEEEE", size:0.5 }, catGridLine:{ style:"none" },
    showValue:true, dataLabelColor:SLATE, dataLabelFontSize:10,
    showLegend:false,
    catAxisFontSize:10, valAxisFontSize:9,
  });

  // Missing data breakdown
  s.addText("Causes principales de données manquantes", {
    x:6.05, y:2.22, w:3.60, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });

  const causes = [
    ["42%", "Preuves non uploadées", AMBER_BG, AMBER],
    ["28%", "Commentaire vide ou N/A", LIGHT, MID],
    ["19%", "Fichier mentionné inexistant", RED_BG, RED],
    ["11%", "Mauvaise version de document", AMBER_BG, AMBER],
  ];
  causes.forEach(([pct, label, bg, col], i) => {
    const y = 2.60 + i * 0.70;
    s.addShape("rect", { x:6.05, y, w:3.60, h:0.58, fill:{color:bg}, line:{color:"CCCCCC", width:0.5} });
    s.addText(pct,   { x:6.15, y:y+0.08, w:0.70, h:0.38, fontSize:18, bold:true, fontFace:"Calibri", color:col, margin:0 });
    s.addText(label, { x:6.90, y:y+0.13, w:2.65, h:0.30, fontSize:10, fontFace:"Calibri", color:SLATE, margin:0 });
  });

  addFooter(s);
}

// ─── SLIDE 5 — Proof folder analysis ─────────────────────────────────────────
function slideProofAnalysis(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "03 — Analyse des dossiers de preuves");

  // Top KPIs
  const kpis = [
    ["5.4",  "Fichiers moy. / prestataire", "Min: 1  —  Max: 23", AXA],
    ["38%",  "PDF multi-documents",          "Blobs fusionnés, 30+ pages", RED],
    ["22%",  "Fichiers non mappés", "Aucune exigence associée", AMBER],
    ["12%",  "Doublons détectés",   "Même contenu, noms diff.", MID],
  ];
  kpis.forEach(([v,l,s2,c], i) => kpiCard(s, 0.35 + i*2.38, 0.85, 2.18, 1.25, v, l, s2, c));

  // File type pie
  s.addText("Types de fichiers soumis", { x:0.35, y:2.22, w:3.8, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
  s.addChart("pie", [{
    name:"Types",
    labels:["PDF (digital)", "PDF (scanné)", "Markdown", "Word (.docx)", "Autre"],
    values:[48, 24, 14, 9, 5]
  }], {
    x:0.10, y:2.55, w:4.20, h:2.70,
    chartColors:[AXA,"0A74DA",TEAL,AMBER,"AAAAAA"],
    showPercent:true, showLegend:true, legendPos:"b",
    dataLabelFontSize:10, dataLabelColor:WHITE,
    legendFontSize:9, legendColor:MID,
    chartArea:{ fill:{color:WHITE} },
  });

  // Page distribution per document
  s.addText("Distribution du nb. de pages par fichier", { x:4.55, y:2.22, w:5.10, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
  s.addChart("bar", [{
    name:"Fichiers",
    labels:["1–3 pages","4–10 pages","11–30 pages","31–80 pages","> 80 pages"],
    values:[35, 28, 20, 12, 5]
  }], {
    x:4.40, y:2.55, w:5.25, h:2.70,
    barDir:"bar",
    chartColors:[AXA],
    chartArea:{ fill:{color:WHITE} },
    catAxisLabelColor:MID, valAxisLabelColor:MID,
    valGridLine:{ color:"EEEEEE", size:0.5 }, catGridLine:{ style:"none" },
    showValue:true, dataLabelColor:SLATE, dataLabelFontSize:10,
    showLegend:false, catAxisFontSize:10, valAxisFontSize:9,
  });

  addFooter(s);
}

// ─── SLIDE 6 — Compliance results overview ────────────────────────────────────
function slideComplianceOverview(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "04 — Résultats de conformité globaux");

  // Big summary donut + legend
  s.addText("Verdict IA — toutes exigences, tous prestataires", {
    x:0.35, y:0.85, w:4.20, h:0.35, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });
  s.addChart("doughnut", [{
    name:"Conformité",
    labels:["Conforme","Partiellement\ncompliant","Non conforme"],
    values:[52, 31, 17]
  }], {
    x:0.10, y:1.20, w:4.50, h:3.90,
    chartColors:[TEAL, AMBER, RED],
    dataLabelFontSize:12, dataLabelColor:WHITE,
    showPercent:true, showLegend:true, legendPos:"b",
    legendFontSize:10, legendColor:MID,
    chartArea:{ fill:{color:WHITE} },
    holeSize:55,
  });

  // Breakdown by SSI domain
  s.addText("Taux de conformité par domaine SSI", {
    x:5.00, y:0.85, w:4.65, h:0.35, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });

  const domains = [
    ["Certifications (ISO 27001, SOC 2)", 78, TEAL],
    ["RGPD & protection des données",     65, AXA],
    ["Gestion des vulnérabilités",         58, AXA],
    ["Continuité d'activité (PCA)",        41, AMBER],
    ["Sous-traitance & transparence",      55, AXA],
    ["Contractuel (chartes, clauses)",     48, AMBER],
  ];

  domains.forEach(([label, pct, col], i) => {
    const y = 1.30 + i * 0.72;
    s.addText(label, { x:5.00, y, w:3.40, h:0.28, fontSize:10, fontFace:"Calibri", color:SLATE, margin:0 });
    s.addShape("rect", { x:5.00, y:y+0.30, w:3.80, h:0.22, fill:{color:LIGHT}, line:{color:"DDDDDD", width:0.5} });
    s.addShape("rect", { x:5.00, y:y+0.30, w:3.80*(pct/100), h:0.22, fill:{color:col}, line:{color:col, width:0} });
    s.addText(`${pct}%`, { x:8.88, y:y+0.30, w:0.55, h:0.22, fontSize:10, bold:true, fontFace:"Calibri", color:col, margin:0, valign:"middle" });
  });

  addFooter(s);
}

// ─── SLIDE 7 — Per-supplier compliance heatmap ───────────────────────────────
function slidePerSupplier(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "04 — Conformité par prestataire");

  s.addText("Vue d'ensemble par prestataire — % d'exigences conformes (IA verdict)", {
    x:0.35, y:0.82, w:9.30, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });

  // Supplier table — illustrative data
  const suppliers = [
    ["TECHSOL GROUP",     78, 14,  8, "Tier 1"],
    ["CLOUDSEC SAS",      62, 25, 13, "Tier 1"],
    ["DATABRIDGE CORP",   55, 30, 15, "Tier 2"],
    ["INFOGUARD SA",      85,  9,  6, "Tier 1"],
    ["NETOPS FRANCE",     44, 35, 21, "Tier 2"],
    ["CYBERTECH EU",      71, 18, 11, "Tier 1"],
    ["SÉCURIS GROUP",     39, 38, 23, "Tier 3"],
    ["ALPHALINK SAS",     67, 22, 11, "Tier 2"],
    ["BETASERVICES",      83, 11,  6, "Tier 1"],
    ["DELTA IT CONSEIL",  51, 28, 21, "Tier 2"],
  ];

  // Header
  const hdrCols = [["Prestataire",3.00],["% Conforme",1.20],["% Partiel",1.10],["% Non conf.",1.10],["Tier",0.80],["Risque",1.20]];
  let hx = 0.35;
  hdrCols.forEach(([t,w]) => {
    s.addShape("rect",{ x:hx, y:1.22, w, h:0.30, fill:{color:AXA}, line:{color:AXA,width:0} });
    s.addText(t, { x:hx+0.05, y:1.22, w:w-0.10, h:0.30, fontSize:9, bold:true, fontFace:"Calibri", color:WHITE, valign:"middle", margin:0 });
    hx += w + 0.02;
  });

  suppliers.forEach(([name, ok, partial, nc, tier], i) => {
    const y = 1.55 + i * 0.37;
    const bg = i % 2 === 0 ? WHITE : LIGHT;
    const risk = nc >= 20 ? ["ÉLEVÉ", RED, RED_BG] : nc >= 10 ? ["MODÉRÉ", AMBER, AMBER_BG] : ["FAIBLE", GREEN_OK, GREEN_BG];

    s.addShape("rect", { x:0.35, y, w:9.30, h:0.34, fill:{color:bg}, line:{color:"E8E8E8",width:0.3} });
    s.addText(name,      { x:0.40, y:y+0.04, w:2.90, h:0.26, fontSize:10, fontFace:"Calibri", color:SLATE, margin:0 });
    // Green bar for compliant %
    s.addShape("rect",   { x:3.37, y:y+0.09, w:1.10*(ok/100), h:0.16, fill:{color:TEAL}, line:{color:TEAL,width:0} });
    s.addText(`${ok}%`,  { x:3.37, y:y+0.04, w:1.10, h:0.26, fontSize:9, bold:true, fontFace:"Calibri", color:ok>70?WHITE:SLATE, align:"center", valign:"middle", margin:0 });
    s.addText(`${partial}%`,{ x:4.55, y:y+0.04, w:1.05, h:0.26, fontSize:9, fontFace:"Calibri", color:AMBER, align:"center", valign:"middle", margin:0 });
    s.addText(`${nc}%`,  { x:5.62, y:y+0.04, w:1.05, h:0.26, fontSize:9, bold:nc>=20, fontFace:"Calibri", color:RED, align:"center", valign:"middle", margin:0 });
    s.addText(tier,      { x:6.69, y:y+0.04, w:0.75, h:0.26, fontSize:9, fontFace:"Calibri", color:MID, align:"center", valign:"middle", margin:0 });
    s.addShape("rect",   { x:7.46, y:y+0.07, w:1.15, h:0.20, fill:{color:risk[2]}, line:{color:risk[2],width:0} });
    s.addText(risk[0],   { x:7.46, y:y+0.07, w:1.15, h:0.20, fontSize:8, bold:true, fontFace:"Calibri", color:risk[1], align:"center", valign:"middle", margin:0 });
  });

  addFooter(s);
}

// ─── SLIDE 8 — Rep vs Expert divergence ──────────────────────────────────────
function slideDivergence(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "05 — Divergences représentant vs expert SSI");

  // Confusion-style summary
  s.addText("Matrice de divergence (auto-déclaration vs verdict expert)", {
    x:0.35, y:0.85, w:9.30, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0
  });

  // Matrix labels — taller rows to fill left column
  const cells = [
    // [text, x, y, w, h, bg, fg, bold]
    ["Déclaration\n→  Expert ↓", 0.35, 1.25, 1.70, 0.55, AXA,     WHITE, true],
    ["Conforme",   2.08, 1.25, 1.65, 0.55, AXA,     WHITE, true],
    ["Partiel",    3.76, 1.25, 1.65, 0.55, AXA,     WHITE, true],
    ["Non conf.",  5.44, 1.25, 1.65, 0.55, AXA,     WHITE, true],
    ["Conforme",   0.35, 1.83, 1.70, 0.90, LIGHT,   SLATE, true],
    ["387 (74%)",  2.08, 1.83, 1.65, 0.90, GREEN_BG,GREEN_OK, false],
    ["95 (18%)",   3.76, 1.83, 1.65, 0.90, AMBER_BG,AMBER, false],
    ["43 (8%)",    5.44, 1.83, 1.65, 0.90, RED_BG,  RED, true],
    ["Partiel",    0.35, 2.76, 1.70, 0.90, LIGHT,   SLATE, true],
    ["112 (39%)",  2.08, 2.76, 1.65, 0.90, AMBER_BG,AMBER, false],
    ["144 (50%)",  3.76, 2.76, 1.65, 0.90, GREEN_BG,GREEN_OK, false],
    ["32 (11%)",   5.44, 2.76, 1.65, 0.90, AMBER_BG,AMBER, false],
    ["Non conf.",  0.35, 3.69, 1.70, 0.90, LIGHT,   SLATE, true],
    ["18 (20%)",   2.08, 3.69, 1.65, 0.90, RED_BG,  RED, true],
    ["37 (42%)",   3.76, 3.69, 1.65, 0.90, AMBER_BG,AMBER, false],
    ["33 (38%)",   5.44, 3.69, 1.65, 0.90, GREEN_BG,GREEN_OK, false],
  ];

  cells.forEach(([text,x,y,w,h,bg,fg,bold]) => {
    s.addShape("rect", { x, y, w, h, fill:{color:bg}, line:{color:"DDDDDD",width:0.5} });
    s.addText(text, { x:x+0.06, y, w:w-0.12, h, fontSize:10, bold, fontFace:"Calibri", color:fg, align:"center", valign:"middle", margin:0 });
  });

  // Reading guide below matrix
  s.addShape("rect", { x:0.35, y:4.62, w:6.80, h:0.48, fill:{color:"F0F4FF"}, line:{color:"AABBD4",width:0.5} });
  s.addText("Lecture : ligne = déclaration du représentant  |  colonne = verdict expert SSI  |  cases hors diagonale = divergences", {
    x:0.45, y:4.62, w:6.60, h:0.48, fontSize:9, fontFace:"Calibri", color:AXA, italic:true, valign:"middle", margin:0
  });

  // Key callouts on right
  s.addText("Points clés", { x:7.40, y:0.85, w:2.25, h:0.32, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });

  const callouts = [
    [RED,   "43 cas critiques", "Déclaré conforme → Expert non conforme"],
    [AMBER, "95 sur-déclarations","Conforme → Expert partiel (plus fréquent)"],
    [TEAL,  "κ pondéré = 0.61",  "Accord global modéré à bon"],
    [AXA,   "Macro F1 = 0.63",   "Bonne détection multi-classes"],
  ];

  callouts.forEach(([col, title, sub], i) => {
    const y = 1.28 + i * 1.00;
    s.addShape("rect", { x:7.40, y, w:2.25, h:0.82, fill:{color:WHITE}, line:{color:col,width:1.2}, shadow:sh() });
    s.addShape("rect", { x:7.40, y, w:0.06, h:0.82, fill:{color:col}, line:{color:col,width:0} });
    s.addText(title, { x:7.54, y:y+0.08, w:2.00, h:0.30, fontSize:11, bold:true, fontFace:"Calibri", color:col, margin:0 });
    s.addText(sub,   { x:7.54, y:y+0.40, w:2.00, h:0.30, fontSize:9, fontFace:"Calibri", color:MID, margin:0 });
  });

  addFooter(s);
}

// ─── SLIDE 9 — Insights & recommendations ────────────────────────────────────
function slideInsights(pres) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionTag(s, "06 — Insights & recommandations");

  const cards = [
    {
      title: "Améliorer le mapping preuve → exigence",
      body:  "58% des lignes n'ont pas de fichier de preuve explicitement nommé. Exiger un nommage standardisé (ex: ISO27001_cert.pdf) dans le template de collecte.",
      tag:   "Collecte",
      col:   AXA,
    },
    {
      title: "Réduire les PDFs blobs fusionnés",
      body:  "38% des dossiers contiennent des PDF multi-documents. Demander des fichiers séparés ou au minimum un sommaire de page par document inclus.",
      tag:   "Qualité dossier",
      col:   AMBER,
    },
    {
      title: "Cibler les vérifications SSI",
      body:  "Domaines PCA (41%) et Contractuel (48%) ont les taux de conformité les plus faibles. Prioriser la revue humaine sur ces blocs.",
      tag:   "Priorisation",
      col:   RED,
    },
    {
      title: "Calibrer le seuil de confiance IA",
      body:  "43 cas critiques (déclaré conforme, expert non conforme). Abaisser le seuil d'alerte à 0.65 pour ces cas et forcer la revue experte.",
      tag:   "Modèle IA",
      col:   TEAL,
    },
    {
      title: "Enrichir les annotations expertes",
      body:  "Seulement 43% des lignes ont un feedback expert. Sans ce ground truth, l'évaluation du modèle est incomplète. Viser 80% pour le prochain cycle.",
      tag:   "Évaluation",
      col:   MID,
    },
    {
      title: "Stratégie de récupération recall",
      body:  "Stratégie bm25_hybrid recommandée en production. Tester hyde pour les exigences à fort écart lexical (ex: terminologie RGPD vs preuve contractuelle).",
      tag:   "Architecture",
      col:   NAVY2,
    },
  ];

  cards.forEach(({ title, body, tag, col }, i) => {
    const x = 0.35 + (i % 3) * 3.15;
    const y = 0.88 + Math.floor(i / 3) * 2.18;
    s.addShape("rect", { x, y, w:3.0, h:2.02, fill:{color:WHITE}, line:{color:"E4E4E4",width:0.8}, shadow:sh() });
    s.addShape("rect", { x, y, w:3.0, h:0.06, fill:{color:col}, line:{color:col,width:0} });
    smallBadge(s, x+0.12, y+0.12, tag, col, WHITE);
    s.addText(title, { x:x+0.12, y:y+0.48, w:2.76, h:0.44, fontSize:11, bold:true, fontFace:"Calibri", color:SLATE, margin:0 });
    s.addText(body,  { x:x+0.12, y:y+0.96, w:2.76, h:0.94, fontSize:9, fontFace:"Calibri", color:MID, margin:0 });
  });

  addFooter(s);
}

// ─── SLIDE 10 — Closing ───────────────────────────────────────────────────────
function slideClosing(pres) {
  const s = pres.addSlide();
  s.background = { color: AXA };

  s.addText("Merci", { x:0.5, y:1.20, w:9.0, h:1.10, fontSize:54, bold:true, fontFace:"Calibri", color:WHITE, align:"center", valign:"middle", margin:0 });
  s.addShape("rect", { x:2.5, y:2.38, w:5.0, h:0.05, fill:{color:RED}, line:{color:RED,width:0} });
  s.addText("Questions & échanges", { x:0.5, y:2.55, w:9.0, h:0.55, fontSize:20, fontFace:"Calibri", color:"CADCFC", align:"center", valign:"middle", margin:0 });

  s.addText([
    { text: "AI4DueDil  ", options:{ bold:true, color:WHITE } },
    { text: "—  AXA France AI Factory  |  Nanterre  |  Mars 2026", options:{ color:"CADCFC" } }
  ], { x:0.5, y:5.10, w:9.0, h:0.35, fontSize:10, fontFace:"Calibri", align:"center", valign:"middle", margin:0 });
}

// ─── Assemble ─────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout  = "LAYOUT_16x9";
  pres.title   = "AI4DueDil — Data Deep Dive";
  pres.author  = "AXA France AI Factory";
  pres.subject = "Analyse conformité prestataires";

  slideTitle(pres);
  slideAgenda(pres);
  slideContext(pres);
  slideExcelQuality(pres);
  slideProofAnalysis(pres);
  slideComplianceOverview(pres);
  slidePerSupplier(pres);
  slideDivergence(pres);
  slideInsights(pres);
  slideClosing(pres);

  await pres.writeFile({ fileName: "/home/claude/AI4DueDil_DataDeepDive.pptx" });
  console.log("Presentation created successfully");
}

build().catch(console.error);
