using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using Michsky.UI.ModernUIPack;
using TMPro;

public class OptionsController : MonoBehaviour {

    [SerializeField] float defaultVolume = 60f;
    [SerializeField] float defaultDifficulty = 0f;
    [SerializeField] string defaultPlayerName = "yedi_player";
    OptionsPlayerName playerNameInputField;
    OptionsDifficultySlider optionsDifficultySlider;
    string playerName;
    Slider difficultySlider;

    void Start ()
    {
        // Hide removed/non-functional UI elements
        VideoObject videoObject = FindAnyObjectByType<VideoObject>();
        if (videoObject != null) videoObject.gameObject.SetActive(false);

        VideoButtonsOptions videoButtons = FindAnyObjectByType<VideoButtonsOptions>();
        if (videoButtons != null) videoButtons.gameObject.SetActive(false);

        // Hide volume slider — audio stays at fixed default for Beat games
        OptionsVolumeSlider optionsVolumeSlider = FindAnyObjectByType<OptionsVolumeSlider>();
        if (optionsVolumeSlider != null) optionsVolumeSlider.gameObject.SetActive(false);

        // Set volume to fixed default
        MusicPlayer musicPlayer = MusicPlayer.Instance;
        if (musicPlayer != null)
            musicPlayer.SetVolume(defaultVolume / 100f);
        PlayerPrefsController.SetMasterVolume(defaultVolume / 100f);

        // Hide the Options Selector (only "Player" remains, arrows are pointless)
        HorizontalSelector selector = FindAnyObjectByType<HorizontalSelector>();
        if (selector != null) selector.gameObject.SetActive(false);

        // Hide Quit button (Application.Quit does nothing in WebGL)
        Button[] allButtons = FindObjectsByType<Button>(FindObjectsSortMode.None);
        foreach (Button btn in allButtons)
        {
            if (btn.gameObject.name == "Quit Button")
                btn.gameObject.SetActive(false);
        }

        // Player name setup
        playerNameInputField = FindAnyObjectByType<OptionsPlayerName>();
        playerName = PlayerPrefsController.GetPlayerName();
        if (string.IsNullOrEmpty(playerName))
            playerName = defaultPlayerName;

        OptionsPlayerNameSaved savedNameDisplay = FindAnyObjectByType<OptionsPlayerNameSaved>();
        if (savedNameDisplay != null)
        {
            Text nameText = savedNameDisplay.GetComponent<Text>();
            if (nameText != null) nameText.text = playerName;
        }

        // Difficulty slider setup
        optionsDifficultySlider = FindAnyObjectByType<OptionsDifficultySlider>();
        if (optionsDifficultySlider != null)
        {
            SliderManager sm = optionsDifficultySlider.GetComponent<SliderManager>();
            if (sm != null)
                difficultySlider = sm.mainSlider;
            else
                difficultySlider = optionsDifficultySlider.GetComponent<Slider>();

            if (difficultySlider != null)
            {
                if (PlayerPrefsController.GetDifficulty() >= 0f)
                    difficultySlider.value = PlayerPrefsController.GetDifficulty();
                else
                    difficultySlider.value = defaultDifficulty;
            }
        }

        // Show both Player Name and Difficulty (no tab switching needed)
        if (playerNameInputField != null) playerNameInputField.gameObject.SetActive(true);
        if (optionsDifficultySlider != null) optionsDifficultySlider.gameObject.SetActive(true);
    }

    public void PlayVideo(string videoURL) { }
    public void HideVideo() { }

    public void SetPlayerName()
    {
        if (playerNameInputField == null) return;
        TMP_InputField inputField = playerNameInputField.GetComponent<TMP_InputField>();
        if (inputField == null) return;
        playerName = inputField.text;
        OptionsPlayerNameSaved savedNameDisplay = FindAnyObjectByType<OptionsPlayerNameSaved>();
        if (savedNameDisplay != null)
        {
            Text nameText = savedNameDisplay.GetComponent<Text>();
            if (nameText != null) nameText.text = playerName;
        }
        PlayerPrefsController.SetPlayerName(playerName);
    }

    public void SetDifficulty()
    {
        if (difficultySlider != null)
            PlayerPrefsController.SetDifficulty(difficultySlider.value);
    }

    IEnumerator SaveAndExit()
    {
        yield return new WaitForSeconds(1);
        PlayerPrefsController.SetPlayerName(playerName);
        SetDifficulty();
        LevelLoader.Instance.LoadMainMenu();
    }

    public void SetDefaults()
    {
        playerName = defaultPlayerName;
        if (difficultySlider != null) difficultySlider.value = defaultDifficulty;
        StartCoroutine(SaveAndExit());
    }

    // Keep these public methods since scene buttons reference them
    public void ActivatePlayerName() { }
    public void ActivateVolumeSlider() { }
    public void ActivateVideo() { }
    public void ActivateDifficultySlider() { }
    public void ActivateAdFree() { }
}
