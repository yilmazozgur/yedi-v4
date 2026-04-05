using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using BayatGames.SaveGameFree;


public class LevelLoader : MonoBehaviour {

    public static LevelLoader Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    int timeToWait = 3;
    public int currentSceneIndex;
    public static int selectedLevel;
    HeptagonController heptagonController;
    string currentScene;

    public bool purchaseGame = true; // Always unlocked
    public bool tutorialPlayed;

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
                LoadSceneSelection();
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
        heptagonController = HeptagonController.Instance;
        currentSceneIndex = SceneManager.GetActiveScene().buildIndex;

        if (currentSceneIndex == 0 || currentSceneIndex == 1)
        {
            Debug.Log("Intro screens");
            StartCoroutine(WaitForTime());
        }
        purchaseGame = true; // Always unlocked
        tutorialPlayed = true; // Skip tutorial by default for AI testbed

        // Hide buttons that don't apply to WebGL AI testbed
        RectTransform playBtnRect = null;
        RectTransform statsBtnRect = null;
        foreach (UnityEngine.UI.Button btn in FindObjectsByType<UnityEngine.UI.Button>(FindObjectsSortMode.None))
        {
            string n = btn.gameObject.name;
            if (n == "Quit Button" || n == "Options Button" || n == "Unlock Button")
                btn.gameObject.SetActive(false);
            else if (n == "Play Button")
                playBtnRect = btn.GetComponent<RectTransform>();
            else if (n == "Stats Button")
                statsBtnRect = btn.GetComponent<RectTransform>();
        }
        // Center the two remaining buttons vertically with spacing
        if (playBtnRect != null)
            playBtnRect.anchoredPosition = new Vector2(playBtnRect.anchoredPosition.x, 120);
        if (statsBtnRect != null)
            statsBtnRect.anchoredPosition = new Vector2(statsBtnRect.anchoredPosition.x, -120);
    }

    public void UpdatePurchaseStatus()
    {
        purchaseGame = true;
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
        currentScene = "Stats Screen Expanded";
        Time.timeScale = 1;
        SceneManager.LoadScene("Stats Screen Expanded");
    }

    public void LoadLevel1()
    {

        Time.timeScale = 1;
        currentScene = "Level 1 Space for Unity";
        SceneManager.LoadScene("Level 1 Space for Unity");

    }

    public void LoadSelectedLevel()
    {
        Debug.Log("LoadSelectedLevel called. selectedLevel=" + selectedLevel + " validSelection=" + (heptagonController != null ? heptagonController.validSelection.ToString() : "null"));
        if (heptagonController != null && heptagonController.validSelection)
        {
            LoadLevel1();
        }
    }

    public void SetSelectedLevel(int selectedLevelMethod)
    {
        selectedLevel = selectedLevelMethod;
        Debug.Log("SetSelectedLevel called with level=" + selectedLevelMethod);
        SaveGame.Save<int>("selectedLevel", selectedLevel);
    }

    public void LoadTutorialLevel()
    {
        selectedLevel = 0;
        tutorialPlayed = true;
        SaveGame.Save<int>("selectedLevel", selectedLevel);
        SaveGame.Save<bool>("tutorialPlayed", tutorialPlayed);
        LoadLevel1();
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
        // Options screen removed for AI testbed
    }

    public void LoadNextScene()
    {
        SceneManager.LoadScene(currentSceneIndex + 1);
    }

    public void QuitGame()
    {
        // Does nothing in WebGL
    }

}
