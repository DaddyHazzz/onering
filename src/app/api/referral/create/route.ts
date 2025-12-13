import { currentUser, clerkClient } from '@clerk/nextjs/server';

export async function GET(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const code = user.id.slice(-6).toUpperCase();

  try {
    const u = await clerkClient.users.getUser(user.id);
    const pm: any = (u.publicMetadata as any) || {};
    if (pm.referralCode !== code) {
      await clerkClient.users.updateUser(user.id, { publicMetadata: { ...pm, referralCode: code } });
    }
  } catch (err: any) {
    console.error('[referral/create] failed to persist code', err);
  }

  return new Response(JSON.stringify({ code }), { status: 200, headers: { 'content-type': 'application/json' } });
}
