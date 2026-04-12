using UnityEngine;

/// <summary>
/// Base class for all card type components (Number, Color, Shape, Word, Beat, Memory, Motor).
/// Handles common mana multiplier caching and CardFrame references.
/// </summary>
public abstract class CardTypeBase : MonoBehaviour
{
    [SerializeField] protected bool activated = false;

    protected CardFrame cardFrameAttached;
    protected Card cardAttached;
    protected bool cardSuper;

    protected float manaReductionMultiplier;
    protected float manaIncreaseMultiplier1;
    protected float manaIncreaseMultiplier2;
    protected float manaIncreaseMultiplier3;

    protected virtual void Start()
    {
        var manaDisplay = ManaDisplay.Instance;
        manaReductionMultiplier = manaDisplay.manaReductionMultiplier;
        manaIncreaseMultiplier1 = manaDisplay.manaIncreaseMultiplier1;
        manaIncreaseMultiplier2 = manaDisplay.manaIncreaseMultiplier2;
        manaIncreaseMultiplier3 = manaDisplay.manaIncreaseMultiplier3;
        cardFrameAttached = GetComponentInParent<CardFrame>();
        cardSuper = cardFrameAttached.cardSuper;
        cardAttached = cardFrameAttached.cardObject;
        // Only reset activated when ActivateComponents() hasn't run yet.
        // When EnsureActivated() fires before this Start(), the card
        // already has valid dimension values. Resetting activated here
        // would cause child Set*() methods to overwrite them with
        // sentinels (colorEmpty, shape index 8, number -1000, etc.).
        if (!cardFrameAttached.IsInitialized)
            activated = false;
    }
}
