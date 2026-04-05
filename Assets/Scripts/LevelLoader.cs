using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using BayatGames.SaveGameFree;
using EasyMobile;


public class LevelLoader : MonoBehaviour {

    public static LevelLoader Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

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
            heptagonController = HeptagonController.Instance;

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
        // Grants the vendor-level consent for AdMob.
        Advertising.GrantDataPrivacyConsent(AdNetwork.AdMob);

        heptagonController = HeptagonController.Instance;
        currentSceneIndex = SceneManager.GetActiveScene().buildIndex;

        if (currentSceneIndex == 0 || currentSceneIndex == 1)
        {
            Debug.Log("Intro secreens");
            StartCoroutine(WaitForTime());
        }
        purchaseGame = SaveGame.Load<bool>("purchaseGame");
        tutorialPlayed = SaveGame.Load<bool>("tutorialPlayed");

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
    }

    public void LoadStats()
    {
        heptagonController = HeptagonController.Instance;
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

        Time.timeScale = 1;
        currentScene = "Level 1 Space for Unity";
        SceneManager.LoadScene("Level 1 Space for Unity");

    }

    public void LoadSelectedLevel()
    {
        // Load the default interstitial ad.
        Advertising.LoadInterstitialAd();

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

    public void QuitGame()
    {
        Application.Quit();
    }

}
