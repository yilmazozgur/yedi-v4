using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using EasyMobile;

public class AdsControllerYedi : MonoBehaviour
{
    public static AdsControllerYedi Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    GameInfo gameInfo;
    GameTimer gameTimer;
    LevelController levelController;

    bool interstitialShown = false;
    string admobID = "ca-app-pub-4928963487858814~8698327100";

    // Subscribe to the event
    void OnEnable()
    {
        Advertising.InterstitialAdCompleted += InterstitialAdCompletedHandler;
        Advertising.RewardedAdCompleted += RewardedAdCompletedHandler;
        Advertising.RewardedAdSkipped += RewardedAdSkippedHandler;

    }

    // The event handler
    void InterstitialAdCompletedHandler(InterstitialAdNetwork network, AdPlacement placement)
    {
        interstitialShown = true;
        Debug.Log("Interstitial ad has been closed.");
        if (gameInfo != null)
        {
            gameInfo.gameObject.SetActive(true);
        }
    }

    // Event handler called when a rewarded ad has completed
    void RewardedAdCompletedHandler(RewardedAdNetwork network, AdPlacement placement)
    {
        Debug.Log("Rewarded ad has completed. The user should be rewarded now.");
        if (gameInfo != null)
        {
            gameInfo.gameObject.SetActive(true);
        }
        if (gameTimer != null)
        {
            gameTimer.TopUpTime();
            gameTimer.gamePaused = true;
        }
        else
        {
            Debug.Log("Timer not topped up!");
        }
        levelController = LevelController.Instance;
        if (levelController != null)
        {
            ChangeLevelController();
        }
        else
        {
            Debug.Log("Level controller not working!");
        }
        Advertising.LoadRewardedAd();
    }

    void ChangeLevelController()
    {
        bool watched = true;
        //levelController.RewardedAdBool(watched);
        levelController.IncrementRewardedNumber();
        levelController.ReturnFromRewardedAd();

    }

    // Event handler called when a rewarded ad has been skipped
    void RewardedAdSkippedHandler(RewardedAdNetwork network, AdPlacement placement)
    {
        Debug.Log("Rewarded ad was skipped. The user should NOT be rewarded.");
        if (gameInfo != null)
        {
            gameInfo.gameObject.SetActive(true);
        }
        Advertising.LoadRewardedAd();
    }

    public bool returninterstitial()
    {
        return interstitialShown;
    }

    // Unsubscribe
    void OnDisable()
    {
        Advertising.InterstitialAdCompleted -= InterstitialAdCompletedHandler;
        Advertising.RewardedAdCompleted -= RewardedAdCompletedHandler;
        Advertising.RewardedAdSkipped -= RewardedAdSkippedHandler;
    }

    // Start is called before the first frame update
    void Start()
    {
        // Grants the vendor-level consent for AdMob.
        Advertising.GrantDataPrivacyConsent(AdNetwork.AdMob);
        gameInfo = FindAnyObjectByType<GameInfo>();
        gameTimer = GameTimer.Instance;
        levelController = LevelController.Instance;

        // Load the default interstitial ad.
        Advertising.LoadInterstitialAd();
        Advertising.LoadRewardedAd();
    }

    public void ShowInterstitialAd()
    {
        // Check if interstitial ad is ready
        bool isReady = Advertising.IsInterstitialAdReady();

        // Show it if it's ready
        if (isReady)
        {
            if (gameInfo != null)
            {
                gameInfo.gameObject.SetActive(false);
            }

            Advertising.ShowInterstitialAd();
        }
        else
        {
            Debug.Log("Ad not ready");
        }
    }

    public void ShowRewardedAd()
    {

        // Check if rewarded ad is ready
        bool isReady = Advertising.IsRewardedAdReady();

        // Show it if it's ready
        if (isReady)
        {
            if (gameInfo != null)
            {
                gameInfo.gameObject.SetActive(false);
            }
            Debug.Log("Rewarded Ad start");
            Advertising.ShowRewardedAd();
        }
        else
        {
            Debug.Log("Ad not ready");
        }

    }



}
