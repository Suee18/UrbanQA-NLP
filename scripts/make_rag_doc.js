// Generates "Germany_RAG_Pipeline.docx" — full pipeline documentation.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType,
  TableOfContents, PageNumber, Header, Footer, PageBreak, ExternalHyperlink,
} = require("docx");

// ── palette ──────────────────────────────────────────────────────────────
const BLUE = "1F4E79", LIGHT = "D5E8F0", GREY = "F2F2F2", ACCENT = "2E75B6";
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const CONTENT_W = 9360;

// ── helpers ────────────────────────────────────────────────────────────────
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const P = (t, opts = {}) => new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: t, ...opts })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 60 }, children: runs(t) });
const num = (t) => new Paragraph({ numbering: { reference: "n", level: 0 }, spacing: { after: 60 }, children: runs(t) });

// support **bold** segments inside a string
function runs(t) {
  const parts = t.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((p) =>
    p.startsWith("**") && p.endsWith("**")
      ? new TextRun({ text: p.slice(2, -2), bold: true })
      : new TextRun(p)
  );
}

function mono(t, opts = {}) {
  return new Paragraph({
    spacing: { after: 40 },
    shading: { fill: GREY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: t, font: "Consolas", size: 18, ...opts })],
  });
}

function cell(text, { head = false, w = 0, bold = false, mono = false } = {}) {
  return new TableCell({
    borders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: head ? BLUE : "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({
      text, bold: head || bold, color: head ? "FFFFFF" : "000000",
      font: mono ? "Consolas" : "Arial", size: mono ? 18 : 20,
    })] })],
  });
}

function table(widths, rows) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, ri) =>
      new TableRow({
        tableHeader: ri === 0,
        children: r.map((c, ci) =>
          typeof c === "string"
            ? cell(c, { head: ri === 0, w: widths[ci] })
            : cell(c.t, { head: ri === 0, w: widths[ci], bold: c.bold, mono: c.mono })
        ),
      })
    ),
  });
}

const codeBlock = (lines) =>
  lines.map((l, i) => mono(l === "" ? " " : l));

// ── document ────────────────────────────────────────────────────────────────
const doc = new Document({
  creator: "UrbanQA",
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: BLUE, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: ACCENT, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] },
      { reference: "n", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Germany RAG  —  ", size: 16, color: "888888" }),
                 new TextRun({ children: ["Page ", PageNumber.CURRENT], size: 16, color: "888888" })],
    })] }) },
    children: [
      // ── Title ──
      new Paragraph({ spacing: { before: 2600, after: 0 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Germany RAG", bold: true, size: 64, color: BLUE })] }),
      new Paragraph({ spacing: { before: 120, after: 0 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "A Retrieval-Augmented Generation Pipeline for German-City Question Answering", size: 26, color: "555555" })] }),
      new Paragraph({ spacing: { before: 200, after: 0 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "LangGraph  ·  Qdrant  ·  BAAI/BGE  ·  Groq Llama-3.3-70B", size: 20, color: ACCENT })] }),
      new Paragraph({ spacing: { before: 1400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "System Documentation", italics: true, size: 22, color: "777777" })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // ── TOC ──
      H1("Contents"),
      new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 1. Overview ──
      H1("1. Overview"),
      P("Germany RAG answers natural-language questions about German cities. The user asks a question; the system retrieves the most relevant passages from a Wikipedia-derived knowledge base and a large language model writes a grounded answer with a source citation."),
      P("It is a classic three-stage RAG loop — Retrieve, Augment, Generate — orchestrated as a LangGraph with three nodes: an LLM query-rewriter, a vector retriever, and a final answer agent. Answers are constrained to the retrieved context, so the system says “I don’t have enough information” rather than hallucinating."),
      H2("Design goals"),
      bullet("**Grounded:** every answer is built only from retrieved Wikipedia context, with citations."),
      bullet("**Modular:** ingestion, embedding, retrieval, and generation are independent, swappable components."),
      bullet("**Free to run:** Qdrant Cloud free tier, open BAAI embeddings, and Groq’s free LLM inference — no paid APIs required."),

      // ── 2. Architecture ──
      H1("2. Architecture"),
      P("The system has two phases. Ingestion runs once to build the knowledge base; the query graph runs per question.", { italics: true }),
      H2("Ingestion (run once)"),
      ...codeBlock([
        "WikipediaLoader (12 German cities)",
        "        |",
        "        v   split into chunks  (chunk_overlap = 0, tagged by city)",
        "        v   embed  (BAAI/bge-large-en-v1.5  ->  1024-dim vectors)",
        "        v",
        "  Qdrant Cloud  ->  ONE collection 'germany_rag'  (1,584 vectors)",
      ]),
      H2("Query graph (LangGraph, per question)"),
      ...codeBlock([
        "  question",
        "     |",
        "     v",
        "  [ NODE 1: rewrite ]   LLM rewrites into a clean, standalone query",
        "     |",
        "     v",
        "  [ NODE 2: retrieve ]  embed query -> Qdrant search (top-k = 10)",
        "     |",
        "     v",
        "  [ NODE 3: answer ]    LLM answers using ONLY the retrieved context",
        "     |",
        "     v",
        "  { answer, sources, rewritten_query, retrieved_docs }",
      ]),

      // ── 3. Tech & models per step ──
      H1("3. Technology & Models per Step"),
      table([720, 2200, 3400, 3040], [
        ["#", "Step", "Technology / Model", "Notes"],
        ["1", "Data collection", "LangChain WikipediaLoader", "12 German cities; one article each"],
        ["2", "Chunking", "RecursiveCharacterTextSplitter", "800 chars, overlap = 0, tagged by location"],
        ["3", "Embedding", "BAAI/bge-large-en-v1.5", "via sentence-transformers; 1024-dim, normalized"],
        ["4", "Vector DB", "Qdrant Cloud", "single collection, cosine distance"],
        ["5", "Query rewrite", "LLM node (System Prompt 1)", "standalone, retrieval-optimized query"],
        ["6", "Retrieval", "Qdrant similarity search", "top-k = 10"],
        ["7", "Answer", "LLM agent (System Prompt 2)", "grounded answer + citation"],
        ["8", "Orchestration", "LangGraph", "3 nodes: rewrite → retrieve → answer"],
        ["9", "LLM backend", "Groq Llama-3.3-70B", "pluggable: local Qwen2.5 / Claude API also supported"],
      ]),
      P(""),
      P("Supporting stack: Python 3.10, PyTorch (CUDA), python-dotenv for secrets, Streamlit + CLI for interfaces.", { size: 18, italics: true, color: "666666" }),

      // ── 4. The two prompts ──
      H1("4. The Two System Prompts"),
      P("The pipeline is driven by exactly two prompts: one shapes the user’s question for retrieval; the other governs the final grounded answer."),
      H2("System Prompt 1 — Query Rewrite Agent"),
      ...codeBlock([
        "You are a query-rewriting assistant for a search system about German",
        "cities and locations. Rewrite the user's question into ONE clean,",
        "standalone search query that maximizes retrieval of relevant facts.",
        "",
        "Rules:",
        "- Make the query self-contained: resolve pronouns to the explicit city.",
        "- Keep and normalize the German location name.",
        "- Remove greetings, chit-chat, and filler; keep only the information need.",
        "- Do NOT answer the question. Output ONLY the rewritten query.",
      ]),
      H2("System Prompt 2 — Final Answer Agent"),
      ...codeBlock([
        "You are a factual assistant that answers questions about German cities",
        "using ONLY the provided context passages.",
        "",
        "Rules:",
        "- Use only facts that appear in the context. No outside knowledge.",
        "- If the context lacks the answer, reply exactly:",
        "  \"I don't have enough information to answer that.\"",
        "- Be concise and accurate.",
        "- End with a short source note naming the location/article used.",
      ]),

      // ── 5. Worked examples ──
      H1("5. Worked Examples (live output)"),
      P("Real runs through the deployed pipeline (Groq Llama-3.3-70B, 1,584-vector index)."),

      H2("Example 1 — fact lookup with pronoun resolution"),
      table([2400, 6960], [
        ["Stage", "Value"],
        [{t:"Question",bold:true}, "how big is the population of munich?"],
        [{t:"Rewritten",bold:true}, "Population of Munich, Germany"],
        [{t:"Answer",bold:true}, "As of 30 November 2024, the population of Munich was 1,604,384. In December 2023, Munich had 1.58 million inhabitants. (Source: Munich — Wikipedia)"],
        [{t:"Retrieved",bold:true}, "10 passages"],
      ]),
      P(""),
      H2("Example 2 — relational fact"),
      table([2400, 6960], [
        ["Stage", "Value"],
        [{t:"Question",bold:true}, "what river flows through cologne?"],
        [{t:"Rewritten",bold:true}, "River flowing through Cologne, Germany"],
        [{t:"Answer",bold:true}, "The Rhine River flows through Cologne. (Source: Cologne — Wikipedia)"],
        [{t:"Retrieved",bold:true}, "10 passages"],
      ]),
      P(""),
      H2("Example 3 — grounded refusal (anti-hallucination)"),
      table([2400, 6960], [
        ["Stage", "Value"],
        [{t:"Question",bold:true}, "what is the average house price in Dresden?"],
        [{t:"Rewritten",bold:true}, "Average house price in Dresden, Germany"],
        [{t:"Answer",bold:true}, "I don't have enough information to answer that. (Source: Dresden — Wikipedia)"],
        [{t:"Retrieved",bold:true}, "10 passages"],
      ]),
      P(""),
      P("Example 3 shows the system declining to invent a figure absent from the context — the core safety property of grounded RAG.", { italics: true, size: 18, color: "666666" }),

      // ── 6. Setup & run ──
      H1("6. Setup & Run"),
      H2("Install"),
      ...codeBlock([
        "pip install -r rag/requirements.txt",
        "cp .env.example .env      # add QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY",
      ]),
      H2("Build the knowledge base (once)"),
      ...codeBlock(["python -m rag.build_index"]),
      H2("Ask a question"),
      ...codeBlock([
        "python -m rag.cli \"How many people live in Munich?\"",
        "streamlit run rag/app.py        # web UI",
      ]),

      // ── 7. Configuration & constraints ──
      H1("7. Configuration & Constraints"),
      P("All tunables live in rag/config.yaml; secrets in .env. Key project constraints encoded in the system:"),
      bullet("**No chunk overlap** — chunk_overlap is fixed at 0; the splitter never duplicates text across chunks."),
      bullet("**Single collection** — the whole corpus lives in one Qdrant collection ('germany_rag'); per-city filtering uses payload metadata, not extra collections."),
      bullet("**Top-k ≤ 15** — retrieval returns 10 passages."),
      bullet("**Chunk by location** — every chunk carries its city in the payload."),
      bullet("**Pluggable LLM** — backend switches between Groq, a local Qwen2.5 model, and the Claude API via one config line."),

      H2("Project layout"),
      table([3000, 6360], [
        ["File", "Role"],
        [{t:"rag/config.yaml",mono:true}, "Cities, models, top-k, backend"],
        [{t:"rag/ingest.py",mono:true}, "WikipediaLoader → chunk → embed → upsert"],
        [{t:"rag/embeddings.py",mono:true}, "BAAI/BGE via sentence-transformers"],
        [{t:"rag/vectorstore.py",mono:true}, "Qdrant single-collection wrapper"],
        [{t:"rag/generator.py",mono:true}, "Pluggable LLM (Groq / local / Claude)"],
        [{t:"rag/prompts.py",mono:true}, "The two system prompts"],
        [{t:"rag/graph.py",mono:true}, "LangGraph: rewrite → retrieve → answer"],
        [{t:"rag/cli.py / rag/app.py",mono:true}, "CLI and Streamlit interfaces"],
      ]),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("Germany_RAG_Pipeline.docx", buf);
  console.log("wrote Germany_RAG_Pipeline.docx");
});
