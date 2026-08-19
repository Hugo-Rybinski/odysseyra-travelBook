import { createContext, useContext } from "react";

// The effective `defaults.*` values of the current draft (with the schema's
// hard fallbacks applied), so a field that inherits an unset value can show it
// in its empty placeholder as "<value> (from defaults.<key>)". Provided by
// EditPanel and read by FieldRow via `spec.inheritsFrom`.
export type EditDefaults = Record<string, string>;

export const EditDefaultsContext = createContext<EditDefaults>({});

export function useEditDefaults(): EditDefaults {
  return useContext(EditDefaultsContext);
}
