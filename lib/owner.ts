const DEFAULT_OWNER_EMAILS = ['elliotbladen@gmail.com'];

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function splitEmails(raw: string | undefined): string[] {
  return (raw ?? '')
    .split(',')
    .map(normalize)
    .filter(Boolean);
}

export function getOwnerEmails(): string[] {
  const emails = [
    ...splitEmails(process.env.OWNER_EMAILS),
    ...splitEmails(process.env.NEXT_PUBLIC_OWNER_EMAIL),
    ...splitEmails(process.env.NEXT_PUBLIC_OWNER_EMAILS),
    ...splitEmails(process.env.NRL_EMAIL),
    ...DEFAULT_OWNER_EMAILS,
  ];
  return Array.from(new Set(emails));
}

export function isOwnerEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  return getOwnerEmails().includes(normalize(email));
}
