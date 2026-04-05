using UnityEngine;

public class AdsControllerYedi : MonoBehaviour
{
    public static AdsControllerYedi Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    public bool returninterstitial()
    {
        return false;
    }

    public void ShowInterstitialAd()
    {
        // Ads removed - no-op
    }

    public void ShowRewardedAd()
    {
        // Ads removed - grant reward directly
        var gameTimer = GameTimer.Instance;
        if (gameTimer != null)
        {
            gameTimer.TopUpTime();
            gameTimer.gamePaused = true;
        }
        var levelController = LevelController.Instance;
        if (levelController != null)
        {
            levelController.IncrementRewardedNumber();
            levelController.ReturnFromRewardedAd();
        }
    }
}
