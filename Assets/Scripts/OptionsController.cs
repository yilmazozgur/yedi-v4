using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Michsky.UI.ModernUIPack;
using TMPro;
using System.Runtime.Serialization.Formatters.Binary;
using System.Runtime.Serialization;
using System.IO;
using EasyMobile;
using LightShaft.Scripts;
//using VoxelBusters.EssentialKit;

public class OptionsController : MonoBehaviour {

    [SerializeField] float defaultVolume = 60f;
    [SerializeField] float defaultDifficulty = 0f;
    [SerializeField] string defaultPlayerName = "yedi_player";
    OptionsPlayerName playerNameInputField;
    OptionsVolumeSlider optionsVolumeSlider;
    OptionsDifficultySlider optionsDifficultySlider;
    string playerName;
    string playerNameServer;
    Slider volumeSlider;
    Slider difficultySlider;

    VideoObject videoObject;
    YoutubePlayer youtubePlayer;
    MusicPlayer musicPlayer;
    VideoButtonsOptions videoButtonsOptions;
    bool musicHalt = false;


    // To store the opened saved game.
    //private SavedGame mySavedGame;

    //private void OnEnable()
    //{
    //    // register for events
    //    CloudServices.OnSynchronizeComplete += OnSynchronizeComplete;
    //}

    //// Register for the CloudServices.OnSyncronizeComplete event
    //// ...
    //private void OnSynchronizeComplete(CloudServicesSynchronizeResult result)
    //{
    //    Debug.Log("Received synchronize finish callback.");
    //    Debug.Log("Status: " + result.Success);
    //    // By this time, you have the latest data from cloud and you can start reading.
    //}

    //private void OnDisable()
    //{
    //    // register for events
    //    CloudServices.OnSynchronizeComplete -= OnSynchronizeComplete;
    //}

    // Use this for initialization

    void Start ()
    {
        videoObject = FindAnyObjectByType<VideoObject>();
        if (videoObject != null)
        {
            youtubePlayer = videoObject.GetComponentInChildren<YoutubePlayer>();
            videoObject.gameObject.SetActive(false);
        }
        videoButtonsOptions = FindAnyObjectByType<VideoButtonsOptions>();
        if(videoButtonsOptions != null)
        {
            videoButtonsOptions.gameObject.SetActive(false);
        }

        musicPlayer = MusicPlayer.Instance;
        playerNameInputField = FindAnyObjectByType<OptionsPlayerName>();
        playerName = PlayerPrefsController.GetPlayerName();
        if (playerName == null || playerName == "")
        {
            playerName = defaultPlayerName;
        }
        FindAnyObjectByType<OptionsPlayerNameSaved>().GetComponent<Text>().text = playerName;

        //CloudServices.Synchronize();
        //playerNameServer = CloudServices.GetString("PlayerName");

        //if (playerNameServer != null && playerNameServer != playerName)
        //{
        //    playerName = playerNameServer;
        //    SetPlayerName();
        //}
        //else if (playerNameServer == null)
        //{
        //    CloudServices.SetString("PlayerName", playerName);
        //}

        optionsVolumeSlider = FindAnyObjectByType<OptionsVolumeSlider>();
        volumeSlider = optionsVolumeSlider.GetComponent<SliderManager>().mainSlider;
        if(PlayerPrefsController.GetMasterVolume() > 0.1f)
        {
            volumeSlider.value = PlayerPrefsController.GetMasterVolume() * 100f;
        }
        else
        {
            volumeSlider.value = defaultVolume;
        }
        AdjustVolume();

        optionsDifficultySlider = FindAnyObjectByType<OptionsDifficultySlider>();
        difficultySlider = optionsDifficultySlider.GetComponent<SliderManager>().mainSlider;
        if (PlayerPrefsController.GetDifficulty() >= 0f)
        {
            difficultySlider.value = PlayerPrefsController.GetDifficulty();
        }
        else
        {
            difficultySlider.value = defaultDifficulty;
        }

        ActivatePlayerName();
    }

    // Update is called once per frame
    void Update ()
    {
        AdjustVolume();
    }


    public void PlayVideo(string videoURL)
    {
        musicPlayer = MusicPlayer.Instance;
        if (musicPlayer != null)
        {
            musicHalt = true;
            musicPlayer.SetVolume(0f);
        }

        if (videoObject != null)
        {
            videoObject.gameObject.SetActive(true);
            if (youtubePlayer != null)
            {
                youtubePlayer.Play(videoURL);
            }
        }


    }

    public void HideVideo()
    {
        if (videoObject != null)
        {
            videoObject.gameObject.SetActive(false);
        }

        musicPlayer = MusicPlayer.Instance;
        if (musicPlayer != null)
        {
            musicHalt = false;
            musicPlayer.SetVolume(PlayerPrefsController.GetMasterVolume());
        }
    }



    private void AdjustVolume()
    {
        if (musicPlayer && musicHalt == false)
        {
            musicPlayer.SetVolume(volumeSlider.value / 100f);
        }

    }

    public void SetPlayerName()
    {
        playerName = playerNameInputField.GetComponent<TMP_InputField>().text;
        FindAnyObjectByType<OptionsPlayerNameSaved>().GetComponent<Text>().text = playerName;
        PlayerPrefsController.SetPlayerName(playerName);
        //CloudServices.SetString("PlayerName", playerName);

    }

    public void SetVolume()
    {
        PlayerPrefsController.SetMasterVolume(volumeSlider.value/100f);
    }

    public void SetDifficulty()
    {
        PlayerPrefsController.SetDifficulty(difficultySlider.value);
    }

    IEnumerator SaveAndExit()
    {
        yield return new WaitForSeconds(1);
        PlayerPrefsController.SetPlayerName(playerName);
        //CloudServices.SetString("PlayerName", playerName);
        SetVolume();
        SetDifficulty();
        LevelLoader.Instance.LoadMainMenu();
    }

    public void SetDefaults()
    {
        playerName = defaultPlayerName;
        volumeSlider.value = defaultVolume * 100;
        AdjustVolume();
        difficultySlider.value = defaultDifficulty;
        StartCoroutine(SaveAndExit());
    }

    private void DeactivateAll()
    {
        playerNameInputField.gameObject.SetActive(false);
        optionsVolumeSlider.gameObject.SetActive(false);
        optionsDifficultySlider.gameObject.SetActive(false);
        videoButtonsOptions.gameObject.SetActive(false);

    }

    public void ActivatePlayerName()
    {
        DeactivateAll();
        playerNameInputField.gameObject.SetActive(true);
    }

    public void ActivateVolumeSlider()
    {
        DeactivateAll();
        optionsVolumeSlider.gameObject.SetActive(true);
    }

    public void ActivateVideo()
    {
        DeactivateAll();
        videoButtonsOptions.gameObject.SetActive(true);
    }

    public void ActivateDifficultySlider()
    {
        DeactivateAll();
        optionsDifficultySlider.gameObject.SetActive(true);
    }

    public void ActivateAdFree()
    {
        DeactivateAll();
    }

    //// Convert an object to a byte array
    //public byte[] ObjectToByteArray(Object obj)
    //{
    //    if (obj == null)
    //        return null;

    //    BinaryFormatter bf = new BinaryFormatter();
    //    MemoryStream ms = new MemoryStream();
    //    bf.Serialize(ms, obj);

    //    return ms.ToArray();
    //}

    //// Convert a byte array to an Object
    //public Object ByteArrayToObject(byte[] arrBytes)
    //{
    //    MemoryStream memStream = new MemoryStream();
    //    BinaryFormatter binForm = new BinaryFormatter();
    //    memStream.Write(arrBytes, 0, arrBytes.Length);
    //    memStream.Seek(0, SeekOrigin.Begin);
    //    Object obj = (Object)binForm.Deserialize(memStream);

    //    return obj;
    //}

    //// Open a saved game with automatic conflict resolution
    //void OpenSavedGame()
    //{
    //    // Open a saved game named "My_Saved_Game" and resolve conflicts automatically if any.
    //    GameServices.SavedGames.OpenWithAutomaticConflictResolution("My_Saved_Game", OpenSavedGameCallback);
    //}

    //// Open saved game callback
    //void OpenSavedGameCallback(SavedGame savedGame, string error)
    //{
    //    if (string.IsNullOrEmpty(error))
    //    {
    //        Debug.Log("Saved game opened successfully!");
    //        mySavedGame = savedGame;        // keep a reference for later operations      
    //    }
    //    else
    //    {
    //        Debug.Log("Open saved game failed with error: " + error);
    //    }
    //}

    //// Updates the given binary data to the specified saved game
    //void WriteSavedGame(SavedGame savedGame, byte[] data)
    //{
    //    if (savedGame.IsOpen)
    //    {
    //        // The saved game is open and ready for writing
    //        GameServices.SavedGames.WriteSavedGameData(
    //            savedGame,
    //            data,
    //            (SavedGame updatedSavedGame, string error) =>
    //            {
    //                if (string.IsNullOrEmpty(error))
    //                {
    //                    Debug.Log("Saved game data has been written successfully!");
    //                }
    //                else
    //                {
    //                    Debug.Log("Writing saved game data failed with error: " + error);
    //                }
    //            }
    
    //        );
    //    }
    //    else
    //    {
    //        // The saved game is not open. You can optionally open it here and repeat the process.
    //        Debug.Log("You must open the saved game before writing to it.");
    //    }
    //}


    //// Retrieves the binary data associated with the specified saved game
    //void ReadSavedGame(SavedGame savedGame)
    //{
    //    if (savedGame.IsOpen)
    //    {
    //        // The saved game is open and ready for reading
    //        GameServices.SavedGames.ReadSavedGameData(
    //            savedGame,
    //            (SavedGame game, byte[] data, string error) =>
    //            {
    //                if (string.IsNullOrEmpty(error))
    //                {
    //                    Debug.Log("Saved game data has been retrieved successfully!");
    //                    // Here you can process the data as you wish.
    //                    if (data.Length > 0)
    //                    {
    //                        // Data processing

    //                    }
    //                    else
    //                    {
    //                        Debug.Log("The saved game has no data!");
    //                    }
    //                }
    //                else
    //                {
    //                    Debug.Log("Reading saved game data failed with error: " + error);
    //                }
    //            }
    
    //        );
    //    }
    //    else
    //    {
    //        // The saved game is not open. You can optionally open it here and repeat the process.
    //        Debug.Log("You must open the saved game before reading its data.");
    //    }
    //}


    //// Deletes a saved game
    //void DeleteSavedGame(SavedGame savedGame)
    //{
    //    GameServices.SavedGames.DeleteSavedGame(savedGame);
    //}

}
