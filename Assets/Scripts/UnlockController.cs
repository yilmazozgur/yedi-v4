using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using EasyMobile;

public class UnlockController : MonoBehaviour
{
    LevelLoader levelLoader;
    HeptagonController heptagonController;
    public bool isInitialized;
    public bool isOwned;
    // Start is called before the first frame update
    void Start()
    {
        isInitialized = InAppPurchasing.IsInitialized();
        levelLoader = FindAnyObjectByType<LevelLoader>();
        heptagonController = FindAnyObjectByType<HeptagonController>();

        if (isInitialized)
        {
            // Get the array of all products created in the In-App Purchasing module settings
            // IAPProduct is the class representing a product as declared in the module settings
            IAPProduct[] products = InAppPurchasing.GetAllIAPProducts();

            // Print all product names
            foreach (IAPProduct prod in products)
            {
                Debug.Log("Product name: " + prod.Name);
            }

            // Check if the product is owned by the user
            // EM_IAPConstants.Sample_Product is the generated name constant of a product named "Sample Product"
            isOwned = InAppPurchasing.IsProductOwned(EM_IAPConstants.Product_unlock);
        }
    }

    public bool ReturnOwnStatus()
    {
        isInitialized = InAppPurchasing.IsInitialized();
        if (isInitialized)
        {
            isOwned = InAppPurchasing.IsProductOwned(EM_IAPConstants.Product_unlock);
            return isOwned;
        }
        else
        {
            return false;
        }

    }

    // Subscribe to IAP purchase events
    void OnEnable()
    {
        InAppPurchasing.PurchaseCompleted += PurchaseCompletedHandler;
        InAppPurchasing.PurchaseFailed += PurchaseFailedHandler;
    }

    // Unsubscribe when the game object is disabled
    void OnDisable()
    {
        InAppPurchasing.PurchaseCompleted -= PurchaseCompletedHandler;
        InAppPurchasing.PurchaseFailed -= PurchaseFailedHandler;
    }

    // Purchase the sample product
    public void PurchaseUnlockProduct()
    {
        levelLoader = FindAnyObjectByType<LevelLoader>();
        heptagonController = FindAnyObjectByType<HeptagonController>();
        if (levelLoader.purchaseGame)
        {
            heptagonController.ShowPurchasedDialog();
        }
        else
        {
            // EM_IAPConstants.Sample_Product is the generated name constant of a product named "Sample Product"
            InAppPurchasing.Purchase(EM_IAPConstants.Product_unlock);
        }
    }

    // Successful purchase handler
    void PurchaseCompletedHandler(IAPProduct product)
    {
        // Compare product name to the generated name constants to determine which product was bought
        switch (product.Name)
        {
            case EM_IAPConstants.Product_unlock:
                Debug.Log("Unlock was purchased. The user should be granted it now.");
                levelLoader = FindAnyObjectByType<LevelLoader>();
                heptagonController = FindAnyObjectByType<HeptagonController>();
                levelLoader.UpdatePurchaseStatus();
                heptagonController.HideUnlockDialog();
                heptagonController.ShowPurchasedDialog();
                break;
        }
    }

    // Failed purchase handler
    void PurchaseFailedHandler(IAPProduct product, string failureReason)
    {
        Debug.Log("The purchase of product " + product.Name + " has failed with reason: " + failureReason);
    }


}
