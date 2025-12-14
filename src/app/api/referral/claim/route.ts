import { currentUser, clerkClient } from '@clerk/nextjs/server';
import { prisma } from '@/lib/db';

async function postReferralToX(referralCode: string, referrerName: string): Promise<boolean> {
  try {
    const referralUrl = `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/referral/${referralCode}`;
    const content = `Join the viral growth revolution with OneRing! 🎯

Use my referral code ${referralCode} to get started:
${referralUrl}

Together we're building the future of social. Let's grow viral content that matters.`;

    // Post to X if Twitter credentials available
    if (
      process.env.TWITTER_API_KEY &&
      process.env.TWITTER_API_SECRET &&
      process.env.TWITTER_ACCESS_TOKEN &&
      process.env.TWITTER_ACCESS_TOKEN_SECRET
    ) {
      const { TwitterApi } = await import('twitter-api-v2');
      const client = new TwitterApi({
        appKey: process.env.TWITTER_API_KEY,
        appSecret: process.env.TWITTER_API_SECRET,
        accessToken: process.env.TWITTER_ACCESS_TOKEN,
        accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
      });

      const tweet = await client.v2.tweet(content);
      console.log('[referral/claim] posted referral to X:', tweet.data.id);
      return true;
    }
    return false;
  } catch (error: any) {
    console.warn('[referral/claim] failed to post referral to X:', error.message);
    return false;
  }
}

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const body = await req.json();
  const code = (body.code || '').toString().toUpperCase();
  if (!code) return new Response(JSON.stringify({ error: 'code required' }), { status: 400, headers: { 'content-type': 'application/json' } });

  try {
    // Find referrer by scanning users for publicMetadata.referralCode
    const list = await clerkClient.users.getUserList({ limit: 100 });
    const ref = list.find((u: any) => ((u.publicMetadata || {}) as any).referralCode === code);
    if (!ref) return new Response(JSON.stringify({ error: 'invalid code' }), { status: 404, headers: { 'content-type': 'application/json' } });

    const referrerId = ref.id;
    if (referrerId === user.id) return new Response(JSON.stringify({ error: 'cannot claim your own code' }), { status: 400, headers: { 'content-type': 'application/json' } });

    // Check claimant hasn't claimed before
    const claimant = await clerkClient.users.getUser(user.id);
    const claimantMeta: any = (claimant.publicMetadata as any) || {};
    if (claimantMeta.referredBy) return new Response(JSON.stringify({ error: 'already claimed' }), { status: 400, headers: { 'content-type': 'application/json' } });

    // Award RING with tier multiplier
    const refMeta: any = (ref.publicMetadata as any) || {};
    const refPrev = Number(refMeta.ring || 0);
    const claimantPrev = Number(claimantMeta.ring || 0);
    const referralCount = Number(refMeta.referralCount || 0);

    // Multiplier: 10+ referrals = 2x RING awards
    const multiplier = referralCount >= 10 ? 2 : 1;
    const baseAward = 200;
    const referrerAward = baseAward * multiplier;
    const claimantBonus = 100; // Extra bonus for new users

    const refNew = refPrev + referrerAward;
    const claimantNew = claimantPrev + claimantBonus;

    // Update Clerk metadata
    await clerkClient.users.updateUser(referrerId, {
      publicMetadata: {
        ...refMeta,
        ring: refNew,
        referralCount: referralCount + 1,
      }
    });
    await clerkClient.users.updateUser(user.id, {
      publicMetadata: {
        ...claimantMeta,
        ring: claimantNew,
        referredBy: referrerId,
      }
    });

    // Update database
    try {
      const referrer = await prisma.user.findUnique({
        where: { clerkId: referrerId },
      });
      const claimantUser = await prisma.user.findUnique({
        where: { clerkId: user.id },
      });

      if (referrer) {
        await prisma.user.update({
          where: { id: referrer.id },
          data: { ringBalance: refNew },
        });
      }
      if (claimantUser) {
        await prisma.user.update({
          where: { id: claimantUser.id },
          data: { ringBalance: claimantNew },
        });
      }
    } catch (dbErr: any) {
      console.warn('[referral/claim] DB update skipped:', dbErr.message);
    }

    // Post referral link to X (bonus +100 RING to referrer)
    const posted = await postReferralToX(code, ref.username || 'OneRing User');
    if (posted) {
      const finalRefBalance = refNew + 100;
      await clerkClient.users.updateUser(referrerId, {
        publicMetadata: { ...refMeta, ring: finalRefBalance, referralCount: referralCount + 1 },
      });
      console.log('[referral/claim] posted referral link to X, awarded +100 RING bonus');
      return new Response(
        JSON.stringify({
          success: true,
          referrerId,
          claimantNew,
          referrerNew: finalRefBalance,
          bonus: '+100 RING for posting referral link to X',
        }),
        { status: 200, headers: { 'content-type': 'application/json' } }
      );
    }

    console.log('[referral/claim] awarded', referrerAward, 'RING to', referrerId, 'and', claimantBonus, 'RING to', user.id);
    return new Response(
      JSON.stringify({
        success: true,
        referrerId,
        claimantNew,
        referrerNew: refNew,
        multiplier,
      }),
      { status: 200, headers: { 'content-type': 'application/json' } }
    );
  } catch (err: any) {
    console.error('[referral/claim] error', err);
    return new Response(JSON.stringify({ error: 'claim failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
