import type { StrategyDescriptor, SchemaProperty } from "../types";

interface Props {
  strategy: StrategyDescriptor;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
}

/**
 * Renders a form from the strategy's pydantic JSON-schema.
 * Every numeric / string / enum field becomes an input; nullable fields
 * accept an empty string which we translate to `null`.
 */
export function StrategyForm({ strategy, values, onChange }: Props) {
  const props = strategy.schema.properties;
  const defs = strategy.schema.$defs ?? {};

  const set = (key: string, v: unknown) => onChange({ ...values, [key]: v });

  return (
    <div>
      {Object.entries(props).map(([key, prop]) => {
        const enumOptions = resolveEnum(prop, defs);
        const isNumber = isNumeric(prop);
        const isNullable = isOptional(prop);
        const current = values[key];

        return (
          <div className="field" key={key}>
            <label title={prop.description ?? ""}>
              {humanise(key)}
              {prop.description && <span className="hint">{prop.description}</span>}
            </label>
            {enumOptions ? (
              <select
                value={current as string}
                onChange={(e) => set(key, e.target.value)}
              >
                {enumOptions.map((opt) => (
                  <option value={opt} key={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={isNumber ? "number" : "text"}
                step={isNumber ? "any" : undefined}
                value={current === null || current === undefined ? "" : String(current)}
                onChange={(e) => {
                  const raw = e.target.value;
                  if (raw === "") {
                    set(key, isNullable ? null : isNumber ? 0 : "");
                  } else if (isNumber) {
                    const n = Number(raw);
                    set(key, Number.isNaN(n) ? raw : n);
                  } else {
                    set(key, raw);
                  }
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

function humanise(k: string): string {
  return k
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isNumeric(p: SchemaProperty): boolean {
  const ts = collectTypes(p);
  return ts.some((t) => t === "number" || t === "integer");
}

function isOptional(p: SchemaProperty): boolean {
  const ts = collectTypes(p);
  return ts.includes("null");
}

function collectTypes(p: SchemaProperty): string[] {
  if (p.anyOf) return p.anyOf.flatMap((x) => (x.type ? [x.type] : []));
  if (Array.isArray(p.type)) return p.type;
  if (p.type) return [p.type];
  return [];
}

function resolveEnum(
  p: SchemaProperty,
  defs: Record<string, { enum?: string[] }>,
): string[] | null {
  if (p.enum) return p.enum;
  // pydantic v2 enums render as {"$ref": "#/$defs/Enumname"}
  const ref = (p as unknown as { $ref?: string }).$ref;
  if (ref?.startsWith("#/$defs/")) {
    const name = ref.slice("#/$defs/".length);
    const def = defs[name];
    if (def?.enum) return def.enum;
  }
  // anyOf with a $ref inside
  if (p.anyOf) {
    for (const a of p.anyOf) {
      const r = (a as unknown as { $ref?: string }).$ref;
      if (r?.startsWith("#/$defs/")) {
        const name = r.slice("#/$defs/".length);
        const def = defs[name];
        if (def?.enum) return def.enum;
      }
    }
  }
  return null;
}
