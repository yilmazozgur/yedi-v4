using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using BayatGames.SaveGameFree;
using EasyMobile;
//using VoxelBusters.EssentialKit;
//using Firebase;
//using Firebase.Database;

public class LevelLoader : MonoBehaviour {

    int timeToWait = 3;
    public int currentSceneIndex;
    public int selectedLevel;
    HeptagonController heptagonController;
    string currentScene;

    public bool purchaseGame;
    public bool tutorialPlayed;
    int numberOfGamesPlayed;
    public int maxFreeGamesForStats = 20;
    UnlockButton unlockButton;
    UnlockController unlockController;
    //DatabaseReference reference;
    

    private void OnApplicationPause(bool pause)
    {
        //Save scene Name if paused, otherwise load last scene
        if (pause)
        {
            SaveGame.Save<string>("currentScene", currentScene);
        }
        else
        {
            //Load last scene
            purchaseGame = SaveGame.Load<bool>("purchaseGame");
            tutorialPlayed = SaveGame.Load<bool>("tutorialPlayed");
            heptagonController = FindAnyObjectByType<HeptagonController>();

            string lastScene = SaveGame.Load<string>("currentScene");

            if(lastScene == "Scene Selection Screen")
            {
                LoadSceneSelection();
            }
            else if (lastScene == "Stats Screen Expanded")
            {
                LoadStats();
            }
            else if (lastScene == "Options Screen")
            {
                LoadOptionsScreen();
            }
            else if (lastScene == "Level 1 Space for Unity")
            {
                selectedLevel = SaveGame.Load<int>("selectedLevel");
                LoadSelectedLevel();
            }
        }
    }

   

    void Start ()
    {

        //Firebase.FirebaseApp.CheckAndFixDependenciesAsync().ContinueWith(task =>
        //{
        //    var dependencyStatus = task.Result;
        //    if (dependencyStatus == Firebase.DependencyStatus.Available)
        //    {
        //        // Create and hold a reference to your FirebaseApp,
        //        // where app is a Firebase.FirebaseApp property of your application class.
        //        //app = Firebase.FirebaseApp.DefaultInstance;

        //        // Set a flag here to indicate whether Firebase is ready to use by your app.
        //    }
        //    else
        //    {
        //        UnityEngine.Debug.LogError(System.String.Format(
        //          "Could not resolve all Firebase dependencies: {0}", dependencyStatus));
        //        // Firebase Unity SDK is not safe to use here.
        //    }
        //});

        // Get the root reference location of the database.
        //reference = FirebaseDatabase.DefaultInstance.RootReference;
        //writeNewUser("0", "try", "try@gmail.com");
        //Firebase.Analytics.FirebaseAnalytics.LogEvent("progress", "percent", 0.4f);

        // Grants the vendor-level consent for AdMob.
        Advertising.GrantDataPrivacyConsent(AdNetwork.AdMob);

        heptagonController = FindAnyObjectByType<HeptagonController>();
        currentSceneIndex = SceneManager.GetActiveScene().buildIndex;

        //!!! ONLY FOR DEBUG PURPOSES, UNLOCKED !!!
        //UpdatePurchaseStatus();
        //!!! ONLY FOR DEBUG PURPOSES, UNLOCKED !!!

        if (currentSceneIndex == 0 || currentSceneIndex == 1)
        {
            Debug.Log("Intro secreens");
            StartCoroutine(WaitForTime());
        }
        purchaseGame = SaveGame.Load<bool>("purchaseGame");
        tutorialPlayed = SaveGame.Load<bool>("tutorialPlayed");

        //if (purchaseGame == true)
        //{
        //    // Remove ads permanently
        //    Advertising.RemoveAds();
        //}

        if (purchaseGame == true)
        {
            unlockButton = FindAnyObjectByType<UnlockButton>();
            if(unlockButton != null)
            {
                unlockButton.gameObject.SetActive(false);
            }
        }
        else
        { //Check whether purchased before
            
            unlockController = FindAnyObjectByType<UnlockController>();
            if(unlockController == null)
            {
                StartCoroutine(InitUnlockObject());
            }
            if(unlockController != null)
            {
                bool isOwned = unlockController.ReturnOwnStatus();
                if(isOwned == true)
                {
                    Debug.Log("Owned the game before");
                    UpdatePurchaseStatus();
                }
            }
        }
       

    }

    IEnumerator InitUnlockObject()
    {
        yield return new WaitForSeconds(0.5f);
        unlockController = FindAnyObjectByType<UnlockController>();
    }

    public void UpdatePurchaseStatus()
    {
        purchaseGame = true;
        SaveGame.Save<bool>("purchaseGame", purchaseGame);
    }

    IEnumerator WaitForTime()
    {
        yield return new WaitForSeconds(timeToWait);
        LoadNextScene();
    }

    public void RestartScene()
    {
        Time.timeScale = 1;
        SceneManager.LoadScene(currentSceneIndex);
    }

    public void LoadMainMenu()
    {
        Time.timeScale = 1;
        currentScene = "Scene Selection Screen";
        SceneManager.LoadScene("Scene Selection Screen");
        //SceneManager.LoadScene("Start Screen");
    }

    public void LoadStats()
    {
        heptagonController = FindAnyObjectByType<HeptagonController>();
        numberOfGamesPlayed = SaveGame.Load<int>("numberOfGamesPlayed");
        purchaseGame = SaveGame.Load<bool>("purchaseGame");
        currentScene = "Stats Screen Expanded";
        if (purchaseGame || numberOfGamesPlayed < maxFreeGamesForStats)
        {
            Time.timeScale = 1;
            SceneManager.LoadScene("Stats Screen Expanded");
        }
        else
        {
            if(heptagonController)
            {
                heptagonController.ShowUnlockDialog();
            }
        }

    }

    public void LoadLevel1()
    {

        //Firebase.Analytics.FirebaseAnalytics.LogEvent(Firebase.Analytics.FirebaseAnalytics.EventLogin);
        Time.timeScale = 1;
        currentScene = "Level 1 Space for Unity";
        SceneManager.LoadScene("Level 1 Space for Unity");

    }

    public void LoadSelectedLevel()
    {
        // Load the default interstitial ad.
        Advertising.LoadInterstitialAd();

        //purchaseGame = true;
        if (purchaseGame || (purchaseGame == false && selectedLevel <= 8))
        {
            if (selectedLevel == 0)
            {
                LoadTutorialLevel();
            }

            if (tutorialPlayed)
            {
                if (heptagonController.validSelection)
                {
                    LoadLevel1(); //Only one scene is enough since levels are adjusted on the script.
                }
            }
            else
            {
                LoadTutorialLevel();
            }
        }
        else
        {
            heptagonController.ShowUnlockDialog();
        }

    }

    public void LoadTutorialLevel()
    {
        selectedLevel = 0;
        tutorialPlayed = true;
        SaveGame.Save<int>("selectedLevel", selectedLevel);
        SaveGame.Save<bool>("tutorialPlayed", tutorialPlayed);
        LoadLevel1();
    }

    public void SetSelectedLevel(int selectedLevelMethod)
    {
        selectedLevel = selectedLevelMethod;
        SaveGame.Save<int>("selectedLevel", selectedLevel);
    }

    public void LoadSceneSelection()
    {
        Time.timeScale = 1;
        FlushAllConfig();
        currentScene = "Scene Selection Screen";
        SceneManager.LoadScene("Scene Selection Screen");
    }

    public void FlushAllConfig()
    {
        // Flush all dimensions
        SaveGame.Save<string>("modeNumber", null);
        SaveGame.Save<string>("modeColor", null);
        SaveGame.Save<string>("modeShape", null);
        SaveGame.Save<string>("modeWord", null);
        SaveGame.Save<string>("modeBeat", null);
        SaveGame.Save<string>("modeMemory", null);
        SaveGame.Save<string>("modeMotor", null);
    }

    public void LoadOptionsScreen()
    {

        currentScene = "Options Screen";
        SceneManager.LoadScene("Options Screen");
    }

    public void LoadNextScene()
    {
        SceneManager.LoadScene(currentSceneIndex + 1);
    }

    //public void RateTheGame()
    //{
    //    StoreReview.RequestRating();
    //}

    public void QuitGame()
    {
        Application.Quit();
    }

    //public void RateMyGame()
    //{
    //    RateMyApp.AskForReviewNow();
    //}

    public class User
    {
        public string username;
        public string email;

        public User()
        {
        }

        public User(string username, string email)
        {
            this.username = username;
            this.email = email;
        }
    }

    //private void writeNewUser(string userId, string name, string email)
    //{
    //    User user = new User(name, email);
    //    string json = JsonUtility.ToJson(user);

    //    //reference.Child("users").Push().SetRawJsonValueAsync(json);
    //    reference.Child("users").Child(userId).SetRawJsonValueAsync(json);
    //}
}
