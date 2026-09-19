function wishKey(wish) {
  if (!wish) return "";
  return wish.id || `${wish.text || ""}\u0000${wish.name || ""}\u0000${wish.createdAt || ""}`;
}

function uniqueWishes(wishes) {
  const seen = new Set();
  const result = [];
  for (const wish of wishes || []) {
    const key = wishKey(wish);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(wish);
  }
  return result;
}

export function createWishPlaybackQueue() {
  const priority = [];
  let replayCycle = [];

  return {
    enqueuePriority(wish) {
      if (wishKey(wish)) priority.push(wish);
    },

    next(history) {
      if (priority.length) {
        return { wish: priority.shift(), source: "priority" };
      }

      const current = uniqueWishes(history);
      if (!current.length) {
        replayCycle = [];
        return null;
      }

      const wishesByKey = new Map(current.map((wish) => [wishKey(wish), wish]));
      replayCycle = replayCycle.filter((key) => wishesByKey.has(key));
      if (!replayCycle.length) replayCycle = current.map(wishKey);

      const key = replayCycle.shift();
      return { wish: wishesByKey.get(key), source: "replay" };
    },

    clear() {
      priority.length = 0;
      replayCycle = [];
    },

    get hasPriority() {
      return priority.length > 0;
    },
  };
}
