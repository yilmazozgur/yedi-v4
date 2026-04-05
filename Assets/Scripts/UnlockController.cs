using UnityEngine;

public class UnlockController : MonoBehaviour
{
    public bool isInitialized = true;
    public bool isOwned = true;

    public bool ReturnOwnStatus()
    {
        return true; // Everything is unlocked
    }

    public void PurchaseUnlockProduct()
    {
        // No-op - everything is free
    }
}
