// src/app/api/referral/leaderboard/route.ts
import { clerkClient } from '@clerk/nextjs/server';

export async function GET() {
  try {
    // Scan all Clerk users and find referral counts
    const list = await clerkClient.users.getUserList({ limit: 100 });

    const leaderboard = list
      .map((user: any) => {
        const meta = (user.publicMetadata || {}) as any;
        return {
          id: user.id,
          username: user.username || `User ${user.id.slice(0, 8)}`,
          referralCount: Number(meta.referralCount || 0),
          ring: Number(meta.ring || 0),
          tier: Number(meta.referralCount || 0) >= 10 ? 'Gold' : 'Silver',
        };
      })
      .filter((u) => u.referralCount > 0)
      .sort((a, b) => b.referralCount - a.referralCount)
      .slice(0, 20); // Top 20

    return new Response(
      JSON.stringify({
        success: true,
        leaderboard,
        lastUpdated: new Date().toISOString(),
      }),
      {
        status: 200,
        headers: { 'content-type': 'application/json' }
      }
    );
  } catch (error: any) {
    console.error('[referral/leaderboard] error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Failed to fetch leaderboard' }),
      {
        status: 500,
        headers: { 'content-type': 'application/json' }
      }
    );
  }
}
