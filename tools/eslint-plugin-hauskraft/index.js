// SPDX-License-Identifier: MIT
// eslint-plugin-hauskraft (M0S-E13-08): `hauskraft/no-raw-styles` keeps UI code on theme tokens
// (AGENTS.md rule 11). It reports colour literals, Tailwind default palette classes, arbitrary values
// and inline colour/font/spacing styles in TS/TSX, and colour literals in CSS (with @eslint/css).
// A line containing `hauskraft-allow-raw-style` is exempt (for data such as theme previews).

const HEX = /(?<![\w&/])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b(?![\w-])/;
const COLOUR_FN = /\b(?:rgba?|hsla?|oklch|oklab|hwb|lab|lch|color)\(/;
const PALETTE = new RegExp(
  "\\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|decoration|shadow|accent|caret|divide|placeholder)-" +
    "(?:(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|" +
    "purple|fuchsia|pink|rose)-(?:50|[1-9]00|950)|white|black)\\b",
);
const ARBITRARY = /\b[a-z][a-z-]*-\[[^\]\s]+\]/;
const ALLOW = "hauskraft-allow-raw-style";

// CSS named colours (CSS Color 4), without transparent and currentColor.
const NAMED = new Set(
  `aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray
lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred
midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple
rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
yellowgreen`.split(/\s+/),
);
const NAMED_WORD = new RegExp(`(?<![\\w-])(?:${[...NAMED].join("|")})(?![\\w-])`, "i");

// Inline style properties that carry colour, font or spacing (custom properties `--x` are data, allowed).
const STYLE_PROP =
  /^(?:color|background(?:Color|Image)?|border(?:Top|Right|Bottom|Left)?(?:Color)?|outline(?:Color)?|fill|stroke|boxShadow|textShadow|caretColor|accentColor|font(?:Family|Size|Weight|Style)?|lineHeight|letterSpacing|(?:padding|margin)(?:Top|Right|Bottom|Left|Inline|Block)?|gap|rowGap|columnGap)$/;
const COLOUR_PROP = /colou?r|background|fill|stroke|border|outline|shadow/i;

/** The first rule a string breaks, in order of how specific the advice is. */
function problemIn(text) {
  if (ARBITRARY.test(text)) return "arbitraryValue";
  if (PALETTE.test(text)) return "paletteClass";
  if (HEX.test(text) || COLOUR_FN.test(text)) return "colourLiteral";
  return null;
}

function keyName(property) {
  if (property.key?.type === "Identifier") return property.key.name;
  if (property.key?.type === "Literal") return String(property.key.value);
  return null;
}

const rule = {
  meta: {
    type: "problem",
    docs: { description: "UI code uses theme tokens and semantic utilities, never raw styles (AGENTS.md rule 11)." },
    messages: {
      colourLiteral: "Colour literal: use a semantic token or utility (bg-primary, text-muted-foreground, …).",
      paletteClass: "Tailwind palette class: use a semantic utility (bg-destructive, text-foreground, …).",
      arbitraryValue: "Arbitrary value: use the theme scale or a named utility in @hauskraft/ui.",
      inlineStyle: "Inline {{prop}} style: use @hauskraft/ui primitives and semantic utilities.",
    },
    schema: [],
  },
  create(context) {
    const source = context.sourceCode;
    const allowed = (node) => {
      const line = node.loc?.start?.line;
      return line !== undefined && source.lines[line - 1]?.includes(ALLOW);
    };
    const report = (node, messageId, data) => {
      if (!allowed(node)) context.report({ node, messageId, data });
    };
    const checkString = (node, text) => {
      if (typeof text !== "string") return;
      const parent = node.parent;
      if (
        parent &&
        ["ImportDeclaration", "ExportNamedDeclaration", "ExportAllDeclaration", "ImportExpression"].includes(
          parent.type,
        )
      )
        return;
      const problem = problemIn(text);
      if (problem) report(node, problem);
    };
    return {
      // TS/TSX
      Literal(node) {
        checkString(node, node.value);
      },
      TemplateElement(node) {
        checkString(node, node.value.cooked);
      },
      Property(node) {
        const key = keyName(node);
        if (!key || key.startsWith("--") || !COLOUR_PROP.test(key)) return;
        if (
          node.value?.type === "Literal" &&
          typeof node.value.value === "string" &&
          NAMED.has(node.value.value.toLowerCase())
        )
          report(node.value, "colourLiteral");
      },
      JSXAttribute(node) {
        if (node.name?.name !== "style" || node.value?.expression?.type !== "ObjectExpression") return;
        for (const property of node.value.expression.properties) {
          const key = property.type === "Property" ? keyName(property) : null;
          if (key && !key.startsWith("--") && STYLE_PROP.test(key)) report(property, "inlineStyle", { prop: key });
        }
      },
      // CSS (@eslint/css)
      Declaration(node) {
        if (typeof node.property === "string" && node.property.startsWith("--")) return;
        const text = source.getText(node.value ?? node);
        if (HEX.test(text) || COLOUR_FN.test(text) || NAMED_WORD.test(text)) report(node, "colourLiteral");
      },
    };
  },
};

export default {
  meta: { name: "eslint-plugin-hauskraft", version: "0.1.0" },
  rules: { "no-raw-styles": rule },
};
