import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Standard shadcn/ui helper: merges Tailwind classes, letting a later
 * conflicting utility (e.g. a caller-supplied className) correctly win
 * over a component's own default instead of both surviving in the DOM. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
