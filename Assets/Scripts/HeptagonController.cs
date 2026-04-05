using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using BayatGames.SaveGameFree;
using LightShaft.Scripts;

public class HeptagonController : MonoBehaviour
{
    HeptagonCanvas heptagonCanvas;
    HeptagonItem[] heptagonItems;

   
    HeptagonItem backgroundHeptagon;

    HeptagonItem helpAnyCombination;

    HeptagonItem maskVisualHeptagon;
    HeptagonItem maskMathHeptagon;
    HeptagonItem maskPhysicalHeptagon;
    HeptagonItem maskMemoryHeptagon;
    HeptagonItem maskMusicHeptagon;
    HeptagonItem maskVerbalHeptagon;
    HeptagonItem maskSpatialHeptagon;

    HeptagonItem buttonVisualHeptagon;
    HeptagonItem buttonMathHeptagon;
    HeptagonItem buttonPhysicalHeptagon;
    HeptagonItem buttonMemoryHeptagon;
    HeptagonItem buttonMusicHeptagon;
    HeptagonItem buttonVerbalHeptagon;
    HeptagonItem buttonSpatialHeptagon;
    HeptagonItem buttonSpatialHeptagon2;
    HeptagonItem buttonSpatialHeptagon3;
    HeptagonItem buttonSpatialHeptagon4;


    HeptagonItem textVisualHeptagon;
    HeptagonItem textMathHeptagon;
    HeptagonItem textPhysicalHeptagon;
    HeptagonItem textMemoryHeptagon;
    HeptagonItem textMusicHeptagon;
    HeptagonItem textVerbalHeptagon;
    HeptagonItem textSpatialHeptagon;

    HeptagonItem mathAddHeptagon;
    HeptagonItem mathMultiplyHeptagon;
    HeptagonItem mathGcdHeptagon;
    HeptagonItem mathVectorHeptagon;
    HeptagonItem mathIntervalHeptagon;
    HeptagonItem mathTrigonlHeptagon;
    HeptagonItem mathSortHeptagon;
    HeptagonItem visualAddHeptagon;
    HeptagonItem visualSubtractHeptagon;
    HeptagonItem visualGrayHeptagon;
    HeptagonItem visualTextHeptagon;
    HeptagonItem spatialTriangleHeptagon;
    HeptagonItem spatialRectangleHeptagon;
    HeptagonItem spatialTripleHeptagon;
    HeptagonItem spatialKanizsaHeptagon;
    HeptagonItem spatialSphereHeptagon;
    HeptagonItem spatiaHanoiHeptagon;
    HeptagonItem verbalVerbsHeptagon;
    HeptagonItem verbalAdjectivesHeptagon;
    HeptagonItem verbalPrepositionsHeptagon;
    HeptagonItem verbalNounsHeptagon;
    HeptagonItem verbalSynVerbsHeptagon;
    HeptagonItem verbalSynAdjectivesHeptagon;
    HeptagonItem verbalGrammarHeptagon;
    HeptagonItem verbalQuestionsHeptagon;
    HeptagonItem verbalScrabbleHeptagon;
    HeptagonItem musicSingleBeatHeptagon;
    HeptagonItem musicDoubleBeatHeptagon;
    HeptagonItem musicDoubleFastBeatHeptagon;
    HeptagonItem musicSingleFastBeatHeptagon;
    HeptagonItem musicTikTokBeatHeptagon;
    HeptagonItem musicFiveBeatHeptagon;
    HeptagonItem memoryEasyHeptagon;
    HeptagonItem memoryMediumHeptagon;
    HeptagonItem memoryHardHeptagon;
    HeptagonItem physicalSpeedAccuracyHeptagon;
    HeptagonItem physicalSpeedAccuracyHalfwayHeptagon;
    HeptagonItem physicalSpeedAccuracyVisitAllHeptagon;

    HeptagonItem heptagonHeptagon;

    Image maskVisualImage;
    Image maskMathImage;
    Image maskPhysicalImage;
    Image maskMemoryImage;
    Image maskMusicImage;
    Image maskVerbalImage;
    Image maskSpatialImage;

    MainCanvas mainCanvas;

    DescriptionController descriptionController;
    GameDescriptionCanvas gameDescriptionCanvas;

    UnlockDialogCanvas unlockDialogCanvas;
    PurchasedDialogCanvas purchasedDialogCanvas;

    LevelLoader levelLoader;

    VideoObject videoObject;
    YoutubePlayer youtubePlayer;
    MusicPlayer musicPlayer;

    string modeNumber;
    string modeColor;
    string modeShape;
    string modeWord;
    string modeBeat;
    string modeMemory;
    string modeMotor;

    bool cycleThrough = false;
    public bool validSelection = false;

    // Start is called before the first frame update
    void Start()
    {
       
        heptagonCanvas = FindAnyObjectByType<HeptagonCanvas>();
        
        levelLoader = FindAnyObjectByType<LevelLoader>();

        videoObject = FindAnyObjectByType<VideoObject>();
        if(videoObject != null)
        {
            youtubePlayer = videoObject.GetComponentInChildren<YoutubePlayer>();
            videoObject.gameObject.SetActive(false);
        }
        


        unlockDialogCanvas = FindAnyObjectByType<UnlockDialogCanvas>();
        if (unlockDialogCanvas)
        {
            unlockDialogCanvas.gameObject.SetActive(false);
        }

        purchasedDialogCanvas = FindAnyObjectByType<PurchasedDialogCanvas>();
        if (purchasedDialogCanvas)
        {
            purchasedDialogCanvas.gameObject.SetActive(false);
        }

        mainCanvas = FindAnyObjectByType<MainCanvas>();
        if (mainCanvas != null)
        {
            FindAllHeptagonItems();
            heptagonCanvas.gameObject.SetActive(false);
        }

        gameDescriptionCanvas = FindAnyObjectByType<GameDescriptionCanvas>();
    }

    public void PlayVideo(string videoURL)
    {
        musicPlayer = FindAnyObjectByType<MusicPlayer>();
        if (musicPlayer != null)
        {
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

        musicPlayer = FindAnyObjectByType<MusicPlayer>();
        if (musicPlayer != null)
        {
            musicPlayer.SetVolume(PlayerPrefsController.GetMasterVolume());
        }
    }

    private void FindAllHeptagonItems()
    {
        descriptionController = FindAnyObjectByType<DescriptionController>();
        heptagonItems = FindObjectsByType<HeptagonItem>(FindObjectsSortMode.None);
        foreach (HeptagonItem heptagonItem in heptagonItems)
        {
            //heptagonItem.gameObject.SetActive(false);

            if (heptagonItem.gameObject.name == "Background")
            {
                heptagonItem.gameObject.SetActive(false);
                backgroundHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Help Button Any")
            {
                heptagonItem.gameObject.SetActive(false);
                helpAnyCombination = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Mask Visual")
            {
                maskVisualImage = heptagonItem.GetComponent<Image>();
                maskVisualHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Math")
            {
                maskMathImage = heptagonItem.GetComponent<Image>();
                maskMathHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Physical")
            {
                maskPhysicalImage = heptagonItem.GetComponent<Image>();
                maskPhysicalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Memory")
            {
                maskMemoryImage = heptagonItem.GetComponent<Image>();
                maskMemoryHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Music")
            {
                maskMusicImage = heptagonItem.GetComponent<Image>();
                maskMusicHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Verbal")
            {
                maskVerbalImage = heptagonItem.GetComponent<Image>();
                maskVerbalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Mask Spatial")
            {
                maskSpatialImage = heptagonItem.GetComponent<Image>();
                maskSpatialHeptagon = heptagonItem;
            }


            if (heptagonItem.gameObject.name == "Button Visual")
            {
                buttonVisualHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Math")
            {
                buttonMathHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Physical")
            {
                buttonPhysicalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Memory")
            {
                buttonMemoryHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Music")
            {
                buttonMusicHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Verbal")
            {
                buttonVerbalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Spatial")
            {
                buttonSpatialHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Spatial2")
            {
                buttonSpatialHeptagon2 = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Spatial3")
            {
                buttonSpatialHeptagon3 = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Button Spatial4")
            {
                buttonSpatialHeptagon4 = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Text Visual")
            {
                heptagonItem.gameObject.SetActive(true);
                textVisualHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Math")
            {
                heptagonItem.gameObject.SetActive(true);
                textMathHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Physical")
            {
                heptagonItem.gameObject.SetActive(true);
                textPhysicalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Memory")
            {
                heptagonItem.gameObject.SetActive(true);
                textMemoryHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Music")
            {
                heptagonItem.gameObject.SetActive(true);
                textMusicHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Verbal")
            {
                heptagonItem.gameObject.SetActive(true);
                textVerbalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Text Spatial")
            {
                heptagonItem.gameObject.SetActive(true);
                textSpatialHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Math Add")
            {
                mathAddHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Multiply")
            {
                mathMultiplyHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Gcd")
            {
                mathGcdHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Vector")
            {
                mathVectorHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Interval")
            {
                mathIntervalHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Trigon")
            {
                mathTrigonlHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Math Sort")
            {
                mathSortHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Visual Add")
            {
                visualAddHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Visual Subtract")
            {
                visualSubtractHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Visual Gray")
            {
                visualGrayHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Visual Text")
            {
                visualTextHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Spatial Triangle")
            {
                spatialTriangleHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Spatial Rectangle")
            {
                spatialRectangleHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Spatial Triple")
            {
                spatialTripleHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Spatial Kanizsa")
            {
                spatialKanizsaHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Spatial Sphere")
            {
                spatialSphereHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Spatial Hanoi")
            {
                spatiaHanoiHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Verbs")
            {
                verbalVerbsHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Verbal Adjectives")
            {
                verbalAdjectivesHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Prepositions")
            {
                verbalPrepositionsHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Nouns")
            {
                verbalNounsHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal SynVerbs")
            {
                verbalSynVerbsHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal SynAdjectives")
            {
                verbalSynAdjectivesHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Grammar")
            {
                verbalGrammarHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Questions")
            {
                verbalQuestionsHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Verbal Scrabble")
            {
                verbalScrabbleHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Music Single Beat")
            {
                musicSingleBeatHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Music Double Beat")
            {
                musicDoubleBeatHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Music Single Fast Beat")
            {
                musicSingleFastBeatHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Music Double Fast Beat")
            {
                musicDoubleFastBeatHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Music TikTok Beat")
            {
                musicTikTokBeatHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Music Five Beat")
            {
                musicFiveBeatHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Memory Easy")
            {
                memoryEasyHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Memory Medium")
            {
                memoryMediumHeptagon = heptagonItem;
            }
            if (heptagonItem.gameObject.name == "Memory Hard")
            {
                memoryHardHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Physical SpeedAccuracy")
            {
                physicalSpeedAccuracyHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Physical SpeedAccuracyHalfway")
            {
                physicalSpeedAccuracyHalfwayHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Physical VisitAll")
            {
                physicalSpeedAccuracyVisitAllHeptagon = heptagonItem;
            }

            if (heptagonItem.gameObject.name == "Heptagon")
            {
                heptagonItem.gameObject.SetActive(true);
                heptagonHeptagon = heptagonItem;
            }
        }
    }

    private void IsValidSelection()
    {
        if(modeNumber == null && modeColor == null && modeShape == null
            && modeWord == null && modeBeat ==null && modeMemory ==null && modeMotor == null)
        {
            validSelection = false;
        }
        else
        {
            validSelection = true;
        }
    }

    public void PrepareSceneSelection()
    {
        FindAllHeptagonItems();
        ActivateHeptagon();
        ActivateAllTexts();
        ActivateAndDimAllMasks();
        DeactivateAllIcons();
        DeactivateAllButtons();
        DeactivateCycleThrough();
        descriptionController.DeactivateAllDescriptions();
    }

    public void PrepareAnyCombinationLevel()
    {
        FlushAllConfig();
        ActivateCycleThrough();
        ActivateAllButtons();
        ActivateAllMasks();
        descriptionController.SetAnyCombinationDescription();
    }

    public void PrepareTutorialLevel()
    {
        descriptionController.SetTutorialDescription();
    }

    public void PrepareWorkoutLevel()
    {
        descriptionController.SetWorkoutDescription();
    }

    public void ShowUnlockDialog()
    {
        if(levelLoader.purchaseGame == true)
        {
            ShowPurchasedDialog();
        }
        else
        {
            if (unlockDialogCanvas)
            {
                unlockDialogCanvas.gameObject.SetActive(true);
                unlockDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(true);
                DeactivateAllButtons();
            }
        }
        
    }

    public void HideUnlockDialog()
    {
        if (levelLoader.purchaseGame == true)
        {
            HidePurchasedDialog();
        }

        if (unlockDialogCanvas)
        {
            unlockDialogCanvas.gameObject.SetActive(false);
            ActivateAllButtons();
            unlockDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(false);
        }
        
        
    }

    public void ShowPurchasedDialog()
    {
        if (purchasedDialogCanvas)
        {
            HideUnlockDialog();
            purchasedDialogCanvas.gameObject.SetActive(true);
            purchasedDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(true);
            DeactivateAllButtons();
        }
    }

    public void HidePurchasedDialog()
    {
        if (purchasedDialogCanvas)
        {
            purchasedDialogCanvas.gameObject.SetActive(false);
            ActivateAllButtons();
            purchasedDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(false);
        }
    }

    public void FlushAllConfig()
    {
        modeNumber = null;
        modeColor = null;
        modeShape = null;
        modeWord = null;
        modeBeat = null;
        modeMemory = null;
        modeMotor = null;
        // Flush all dimensions
        SaveGame.Save<string>("modeNumber", null);
        SaveGame.Save<string>("modeColor", null);
        SaveGame.Save<string>("modeShape", null);
        SaveGame.Save<string>("modeWord", null);
        SaveGame.Save<string>("modeBeat", null);
        SaveGame.Save<string>("modeMemory", null);
        SaveGame.Save<string>("modeMotor", null);
    }

    public void HeptagonShowHelp()
    {
        string modeNumberHelp = SaveGame.Load<string>("modeNumber");
        string modeColorHelp = SaveGame.Load<string>("modeColor");
        string modeShapeHelp = SaveGame.Load<string>("modeShape");
        string modeWordHelp = SaveGame.Load<string>("modeWord");
        string modeBeatHelp = SaveGame.Load<string>("modeBeat");
        string modeMemoryHelp = SaveGame.Load<string>("modeMemory");
        string modeMotorHelp = SaveGame.Load<string>("modeMotor");

        cycleThrough = false;

        FindAllHeptagonItems();

        heptagonCanvas.gameObject.SetActive(true);
        backgroundHeptagon.gameObject.SetActive(true);
        ActivateHeptagon();
        ActivateAndDimAllMasks();
        ActivateAllTexts();

        DeactivateAllButtons();
        DeactivateAllIcons();
        DimAllMasks();

        gameDescriptionCanvas.gameObject.SetActive(true);

        bool highlighted = false;

        if (modeNumberHelp == "add")
        {
            ActivateMathAdd();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "multiply")
        {
            ActivateMathMultiply();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "gcd")
        {
            ActivateMathGcd();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "vector")
        {
            ActivateMathVector();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "interval")
        {
            ActivateMathInterval();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "trigon")
        {
            ActivateMathTrigon();
            HighlightMaskMath();
            highlighted = true;
        }
        else if (modeNumberHelp == "sort")
        {
            ActivateMathSort();
            HighlightMaskMath();
            highlighted = true;
        }

        if (modeColorHelp == "add")
        {
            ActivateVisualAdd();
            if(!highlighted)
            {
                HighlightMaskVisual();
                highlighted = true;
            }
        }
        else if(modeColorHelp == "subtract")
        {
            ActivateVisualSubtract();
            if (!highlighted)
            {
                HighlightMaskVisual();
                highlighted = true;
            }
        }
        else if (modeColorHelp == "gray")
        {
            ActivateVisualGray();
            if (!highlighted)
            {
                HighlightMaskVisual();
                highlighted = true;
            }
        }
        else if (modeColorHelp == "text")
        {
            ActivateVisualText();
            if (!highlighted)
            {
                HighlightMaskVisual();
                highlighted = true;
            }
        }

        if (modeShapeHelp == "triangle")
        {
            ActivateSpatialTriangle();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }
        else if(modeShapeHelp == "rectangle")
        {
            ActivateSpatialRectangle();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }
        else if (modeShapeHelp == "triple")
        {
            ActivateSpatialTriple();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }
        else if (modeShapeHelp == "kanizsa")
        {
            ActivateSpatialKanizsa();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }
        else if (modeShapeHelp == "sphere")
        {
            ActivateSpatialSphere();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }
        else if (modeShapeHelp == "hanoi")
        {
            ActivateSpatialHanoi();
            if (!highlighted)
            {
                HighlightMaskSpatial();
                highlighted = true;
            }
        }

        if (modeWordHelp == "verbs")
        {
            ActivateVerbalVerbs();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "adjectives")
        {
            ActivateVerbalAdjectives();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "prepositions")
        {
            ActivateVerbalPrepositions();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "nouns")
        {
            ActivateVerbalNouns();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "synVerbs")
        {
            ActivateVerbalSynVerbs();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "synAdjectives")
        {
            ActivateVerbalSynAdjectives();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "grammar")
        {
            ActivateVerbalGrammar();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "questions")
        {
            ActivateVerbalQuestions();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }
        else if (modeWordHelp == "scrabble")
        {
            ActivateVerbalScrabble();
            if (!highlighted)
            {
                HighlightMaskVerbal();
                highlighted = true;
            }
        }

        if (modeBeatHelp == "single")
        {
            ActivateSingleBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }
        else if (modeBeatHelp == "double")
        {
            ActivateDoubleBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }
        else if (modeBeatHelp == "double fast")
        {
            ActivateDoubleFastBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }
        else if (modeBeatHelp == "single fast")
        {
            ActivateSingleFastBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }
        else if (modeBeatHelp == "tiktok")
        {
            ActivateTikTokBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }
        else if (modeBeatHelp == "five")
        {
            ActivateFiveBeat();
            if (!highlighted)
            {
                HighlightMaskMusic();
                highlighted = true;
            }
        }

        if (modeMemoryHelp == "every action")
        {
            ActivateMemoryEasy();
            if (!highlighted)
            {
                HighlightMaskMemory();
                highlighted = true;
            }
        }
        else if (modeMemoryHelp == "show all")
        {
            ActivateMemoryMedium();
            if (!highlighted)
            {
                HighlightMaskMemory();
                highlighted = true;
            }
        }
        else if (modeMemoryHelp == "show one")
        {
            ActivateMemoryHard();
            if (!highlighted)
            {
                HighlightMaskMemory();
                highlighted = true;
            }
        }

        if (modeMotorHelp == "speed accuracy")
        {
            ActivatePhysicalSpeedAccuracy();
            if (!highlighted)
            {
                HighlightMaskPhysical();
                highlighted = true;
            }
        }

        if (modeMotorHelp == "speed accuracy halfway")
        {
            ActivatePhysicalSpeedAccuracyHalfway();
            if (!highlighted)
            {
                HighlightMaskPhysical();
                highlighted = true;
            }
        }

        if (modeMotorHelp == "visit all slots")
        {
            ActivatePhysicalSpeedAccuracyVisitAll();
            if (!highlighted)
            {
                HighlightMaskPhysical();
                highlighted = true;
            }
        }

    }

    public void ActivateCycleThrough()
    {
        cycleThrough = true;
    }

    public void DeactivateCycleThrough()
    {
        cycleThrough = false;
    }

    public void HeptagonHideHelp()
    {
        FindAllHeptagonItems();
        //heptagonCanvas = FindAnyObjectByType<HeptagonCanvas>();
        heptagonCanvas.gameObject.SetActive(false);
        gameDescriptionCanvas.gameObject.SetActive(false);
        //descriptionController.HideDescriptions();
    }

    public void ActivateAllTexts()
    {
        ActivateTextMath();
        ActivateTextMemory();
        ActivateTextMusic();
        ActivateTextPhysical();
        ActivateTextSpatial();
        ActivateTextVerbal();
        ActivateTextVisual();
    }

    public void DimAllMasks()
    {
        DimMaskVisual();
        DimMaskMath();
        DimMaskPhysical();
        DimMaskMemory();
        DimMaskMusic();
        DimMaskVerbal();
        DimMaskSpatial();
    }

    public void ActivateAndDimAllMasks()
    {
        ActivateMaskVisual();
        DimMaskVisual();
        ActivateMaskMath();
        DimMaskMath();
        ActivateMaskPhysical();
        DimMaskPhysical();
        ActivateMaskMemory();
        DimMaskMemory();
        ActivateMaskMusic();
        DimMaskMusic();
        ActivateMaskVerbal();
        DimMaskVerbal();
        ActivateMaskSpatial();
        DimMaskSpatial();
    }

    public void TurnOffMath()
    {
        DimMaskMath();
        mathAddHeptagon.gameObject.SetActive(false);
        mathMultiplyHeptagon.gameObject.SetActive(false);
        mathGcdHeptagon.gameObject.SetActive(false);
        mathVectorHeptagon.gameObject.SetActive(false);
        mathIntervalHeptagon.gameObject.SetActive(false);
        mathTrigonlHeptagon.gameObject.SetActive(false);
        mathSortHeptagon.gameObject.SetActive(false);
        modeNumber = null;
    }

    public void TurnOffVisual()
    {
        DimMaskVisual();
        visualAddHeptagon.gameObject.SetActive(false);
        visualSubtractHeptagon.gameObject.SetActive(false);
        visualGrayHeptagon.gameObject.SetActive(false);
        visualTextHeptagon.gameObject.SetActive(false);
        modeColor = null;
    }

    public void TurnOffSpatial()
    {
        DimMaskSpatial();
        spatialTriangleHeptagon.gameObject.SetActive(false);
        spatialRectangleHeptagon.gameObject.SetActive(false);
        spatialTripleHeptagon.gameObject.SetActive(false);
        spatialKanizsaHeptagon.gameObject.SetActive(false);
        spatialSphereHeptagon.gameObject.SetActive(false);
        spatiaHanoiHeptagon.gameObject.SetActive(false);
        modeShape = null;
    }

    public void TurnOffVerbal()
    {
        DimMaskVerbal();
        verbalVerbsHeptagon.gameObject.SetActive(false);
        verbalAdjectivesHeptagon.gameObject.SetActive(false);
        verbalPrepositionsHeptagon.gameObject.SetActive(false);
        verbalNounsHeptagon.gameObject.SetActive(false);
        verbalSynVerbsHeptagon.gameObject.SetActive(false);
        verbalSynAdjectivesHeptagon.gameObject.SetActive(false);
        verbalGrammarHeptagon.gameObject.SetActive(false);
        verbalQuestionsHeptagon.gameObject.SetActive(false);
        verbalScrabbleHeptagon.gameObject.SetActive(false);
        modeWord = null;
    }

    public void TurnOffMusic()
    {
        DimMaskMusic();
        musicDoubleBeatHeptagon.gameObject.SetActive(false);
        musicSingleBeatHeptagon.gameObject.SetActive(false);
        musicDoubleFastBeatHeptagon.gameObject.SetActive(false);
        musicSingleFastBeatHeptagon.gameObject.SetActive(false);
        musicTikTokBeatHeptagon.gameObject.SetActive(false);
        musicFiveBeatHeptagon.gameObject.SetActive(false);
        modeBeat = null;
    }

    public void TurnOffMemory()
    {
        DimMaskMemory();
        memoryEasyHeptagon.gameObject.SetActive(false);
        memoryMediumHeptagon.gameObject.SetActive(false);
        memoryHardHeptagon.gameObject.SetActive(false);
        modeMemory = null;
    }

    public void TurnOffPhysical()
    {
        DimMaskPhysical();
        physicalSpeedAccuracyHeptagon.gameObject.SetActive(false);
        physicalSpeedAccuracyHalfwayHeptagon.gameObject.SetActive(false);
        physicalSpeedAccuracyVisitAllHeptagon.gameObject.SetActive(false);
        modeMotor = null;
    }

    public void PrepareMath()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskMath();
        ActivateButtonMath();
    }
    public void PrepareVisual()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskVisual();
        ActivateButtonVisual();
    }
    public void PrepareSpatial()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskSpatial();
        ActivateButtonSpatial();
    }
    public void PrepareVerbal()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskVerbal();
        ActivateButtonVerbal();
    }
    public void PrepareMusic()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskMusic();
        ActivateButtonMusic();
    }
    public void PrepareMemory()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskMemory();
        ActivateButtonMemory();
    }
    public void PreparePhysical()
    {
        //DeactivateAllMasks();
        //DeactivateAllButtons();
        ActivateMaskPhysical();
        ActivateButtonPhysical();
    }


    public void DeactivateAllMasks()
    {
        maskVisualHeptagon.gameObject.SetActive(false);
        maskMathHeptagon.gameObject.SetActive(false);
        maskPhysicalHeptagon.gameObject.SetActive(false);
        maskMemoryHeptagon.gameObject.SetActive(false);
        maskMusicHeptagon.gameObject.SetActive(false);
        maskVerbalHeptagon.gameObject.SetActive(false);
        maskSpatialHeptagon.gameObject.SetActive(false);
    }

    public void DeactivateAllButtons()
    {
        buttonVisualHeptagon.gameObject.SetActive(false);
        buttonMathHeptagon.gameObject.SetActive(false);
        buttonPhysicalHeptagon.gameObject.SetActive(false);
        buttonMemoryHeptagon.gameObject.SetActive(false);
        buttonMusicHeptagon.gameObject.SetActive(false);
        buttonVerbalHeptagon.gameObject.SetActive(false);
        buttonSpatialHeptagon.gameObject.SetActive(false);
        buttonSpatialHeptagon2.gameObject.SetActive(false);
        buttonSpatialHeptagon3.gameObject.SetActive(false);
        buttonSpatialHeptagon4.gameObject.SetActive(false);
    }

    public void ActivateAllButtons()
    {
        buttonVisualHeptagon.gameObject.SetActive(true);
        buttonMathHeptagon.gameObject.SetActive(true);
        buttonPhysicalHeptagon.gameObject.SetActive(true);
        buttonMemoryHeptagon.gameObject.SetActive(true);
        buttonMusicHeptagon.gameObject.SetActive(true);
        buttonVerbalHeptagon.gameObject.SetActive(true);
        buttonSpatialHeptagon.gameObject.SetActive(true);
        buttonSpatialHeptagon2.gameObject.SetActive(true);
        buttonSpatialHeptagon3.gameObject.SetActive(true);
        buttonSpatialHeptagon4.gameObject.SetActive(true);
    }

    public void ActivateAllMasks()
    {
        maskVisualHeptagon.gameObject.SetActive(true);
        maskMathHeptagon.gameObject.SetActive(true);
        maskPhysicalHeptagon.gameObject.SetActive(true);
        maskMemoryHeptagon.gameObject.SetActive(true);
        maskMusicHeptagon.gameObject.SetActive(true);
        maskVerbalHeptagon.gameObject.SetActive(true);
        maskSpatialHeptagon.gameObject.SetActive(true);
    }

    public void ActivateMaskVisual()
    {
        maskVisualHeptagon.gameObject.SetActive(true);
        Color maskColor = maskVisualImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskVisualImage.color = maskColor;
    }
    public void ActivateMaskMath()
    {
        maskMathHeptagon.gameObject.SetActive(true);
        Color maskColor = maskMathImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskMathImage.color = maskColor;
    }
    public void ActivateMaskPhysical()
    {
        maskPhysicalHeptagon.gameObject.SetActive(true);
        Color maskColor = maskPhysicalImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskPhysicalImage.color = maskColor;
    }
    public void ActivateMaskMemory()
    {
        maskMemoryHeptagon.gameObject.SetActive(true);
        Color maskColor = maskMemoryImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskMemoryImage.color = maskColor;
    }
    public void ActivateMaskMusic()
    {
        maskMusicHeptagon.gameObject.SetActive(true);
        Color maskColor = maskMusicImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskMusicImage.color = maskColor;
    }
    public void ActivateMaskVerbal()
    {
        maskVerbalHeptagon.gameObject.SetActive(true);
        Color maskColor = maskVerbalImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskVerbalImage.color = maskColor;
    }
    public void ActivateMaskSpatial()
    {
        maskSpatialHeptagon.gameObject.SetActive(true);
        Color maskColor = maskSpatialImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskColor.a = 1f;
        maskSpatialImage.color = maskColor;
    }

    public void ActivateTextVisual()
    {
        textVisualHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextMath()
    {
        textMathHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextPhysical()
    {
        textPhysicalHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextMemory()
    {
        textMemoryHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextMusic()
    {
        textMusicHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextVerbal()
    {
        textVerbalHeptagon.gameObject.SetActive(true);
    }
    public void ActivateTextSpatial()
    {
        textSpatialHeptagon.gameObject.SetActive(true);
    }


    public void DeactivateAllIcons()
    {
        mathAddHeptagon.gameObject.SetActive(false);
        mathMultiplyHeptagon.gameObject.SetActive(false);
        mathGcdHeptagon.gameObject.SetActive(false);
        mathVectorHeptagon.gameObject.SetActive(false);
        mathIntervalHeptagon.gameObject.SetActive(false);
        mathTrigonlHeptagon.gameObject.SetActive(false);
        mathSortHeptagon.gameObject.SetActive(false);
        visualAddHeptagon.gameObject.SetActive(false);
        visualSubtractHeptagon.gameObject.SetActive(false);
        visualGrayHeptagon.gameObject.SetActive(false);
        visualTextHeptagon.gameObject.SetActive(false);
        spatialTriangleHeptagon.gameObject.SetActive(false);
        spatialRectangleHeptagon.gameObject.SetActive(false);
        spatialTripleHeptagon.gameObject.SetActive(false);
        spatialKanizsaHeptagon.gameObject.SetActive(false);
        spatialSphereHeptagon.gameObject.SetActive(false);
        spatiaHanoiHeptagon.gameObject.SetActive(false);
        verbalVerbsHeptagon.gameObject.SetActive(false);
        verbalAdjectivesHeptagon.gameObject.SetActive(false);
        verbalPrepositionsHeptagon.gameObject.SetActive(false);
        verbalNounsHeptagon.gameObject.SetActive(false);
        verbalSynVerbsHeptagon.gameObject.SetActive(false);
        verbalSynAdjectivesHeptagon.gameObject.SetActive(false);
        verbalGrammarHeptagon.gameObject.SetActive(false);
        verbalQuestionsHeptagon.gameObject.SetActive(false);
        verbalScrabbleHeptagon.gameObject.SetActive(false);
        musicSingleBeatHeptagon.gameObject.SetActive(false);
        musicDoubleBeatHeptagon.gameObject.SetActive(false);
        musicDoubleFastBeatHeptagon.gameObject.SetActive(false);
        musicSingleFastBeatHeptagon.gameObject.SetActive(false);
        musicTikTokBeatHeptagon.gameObject.SetActive(false);
        musicFiveBeatHeptagon.gameObject.SetActive(false);
        memoryEasyHeptagon.gameObject.SetActive(false);
        memoryMediumHeptagon.gameObject.SetActive(false);
        memoryHardHeptagon.gameObject.SetActive(false);
        physicalSpeedAccuracyHeptagon.gameObject.SetActive(false);
        physicalSpeedAccuracyHalfwayHeptagon.gameObject.SetActive(false);
        physicalSpeedAccuracyVisitAllHeptagon.gameObject.SetActive(false);
    }

    public void ActivateHelpAnyCombination()
    {
        helpAnyCombination.gameObject.SetActive(true);
    }

    public void ActivateMathAdd()
    {
        PrepareMath();
        mathAddHeptagon.gameObject.SetActive(true);
        modeNumber = "add";
    }
    public void ActivateMathMultiply()
    {
        PrepareMath();
        mathMultiplyHeptagon.gameObject.SetActive(true);
        modeNumber = "multiply";
    }
    public void ActivateMathGcd()
    {
        PrepareMath();
        mathGcdHeptagon.gameObject.SetActive(true);
        modeNumber = "gcd";
    }
    public void ActivateMathVector()
    {
        PrepareMath();
        mathVectorHeptagon.gameObject.SetActive(true);
        modeNumber = "vector";
    }
    public void ActivateMathInterval()
    {
        PrepareMath();
        mathIntervalHeptagon.gameObject.SetActive(true);
        modeNumber = "interval";
    }
    public void ActivateMathTrigon()
    {
        PrepareMath();
        mathTrigonlHeptagon.gameObject.SetActive(true);
        modeNumber = "trigon";
    }
    public void ActivateMathSort()
    {
        PrepareMath();
        mathSortHeptagon.gameObject.SetActive(true);
        modeNumber = "sort";
    }

    public void ActivateVisualAdd()
    {
        PrepareVisual();
        visualAddHeptagon.gameObject.SetActive(true);
        modeColor = "add";
    }
    public void ActivateVisualSubtract()
    {
        PrepareVisual();
        visualSubtractHeptagon.gameObject.SetActive(true);
        modeColor = "subtract";
    }
    public void ActivateVisualGray()
    {
        PrepareVisual();
        visualGrayHeptagon.gameObject.SetActive(true);
        modeColor = "gray";
    }
    public void ActivateVisualText()
    {
        PrepareVisual();
        visualTextHeptagon.gameObject.SetActive(true);
        modeColor = "text";
    }

    public void ActivateSpatialTriangle()
    {
        PrepareSpatial();
        spatialTriangleHeptagon.gameObject.SetActive(true);
        modeShape = "triangle";
    }
    public void ActivateSpatialRectangle()
    {
        PrepareSpatial();
        modeShape = "rectangle";
        spatialRectangleHeptagon.gameObject.SetActive(true);
    }
    public void ActivateSpatialTriple()
    {
        PrepareSpatial();
        modeShape = "triple";
        spatialTripleHeptagon.gameObject.SetActive(true);
    }
    public void ActivateSpatialKanizsa()
    {
        PrepareSpatial();
        modeShape = "kanizsa";
        spatialKanizsaHeptagon.gameObject.SetActive(true);
    }
    public void ActivateSpatialSphere()
    {
        PrepareSpatial();
        modeShape = "sphere";
        spatialSphereHeptagon.gameObject.SetActive(true);
    }
    public void ActivateSpatialHanoi()
    {
        PrepareSpatial();
        modeShape = "hanoi";
        spatiaHanoiHeptagon.gameObject.SetActive(true);
    }

    public void ActivateVerbalVerbs()
    {
        PrepareVerbal();
        verbalVerbsHeptagon.gameObject.SetActive(true);
        modeWord = "verbs";
    }
    public void ActivateVerbalAdjectives()
    {
        PrepareVerbal();
        verbalAdjectivesHeptagon.gameObject.SetActive(true);
        modeWord = "adjectives";
    }

    public void ActivateVerbalPrepositions()
    {
        PrepareVerbal();
        verbalPrepositionsHeptagon.gameObject.SetActive(true);
        modeWord = "prepositions";
    }

    public void ActivateVerbalNouns()
    {
        PrepareVerbal();
        verbalNounsHeptagon.gameObject.SetActive(true);
        modeWord = "nouns";
    }

    public void ActivateVerbalSynVerbs()
    {
        PrepareVerbal();
        verbalSynVerbsHeptagon.gameObject.SetActive(true);
        modeWord = "synVerbs";
    }

    public void ActivateVerbalSynAdjectives()
    {
        PrepareVerbal();
        verbalSynAdjectivesHeptagon.gameObject.SetActive(true);
        modeWord = "synAdjectives";
    }

    public void ActivateVerbalGrammar()
    {
        PrepareVerbal();
        verbalGrammarHeptagon.gameObject.SetActive(true);
        modeWord = "grammar";
    }

    public void ActivateVerbalQuestions()
    {
        PrepareVerbal();
        verbalQuestionsHeptagon.gameObject.SetActive(true);
        modeWord = "questions";
    }

    public void ActivateVerbalScrabble()
    {
        PrepareVerbal();
        verbalScrabbleHeptagon.gameObject.SetActive(true);
        modeWord = "scrabble";
    }

    public void ActivateSingleBeat()
    {
        PrepareMusic();
        musicSingleBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "single";
    }
    public void ActivateDoubleBeat()
    {
        PrepareMusic();
        musicDoubleBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "double";
    }
    public void ActivateDoubleFastBeat()
    {
        PrepareMusic();
        musicDoubleFastBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "double fast";
    }
    public void ActivateSingleFastBeat()
    {
        PrepareMusic();
        musicSingleFastBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "single fast";
    }
    public void ActivateTikTokBeat()
    {
        PrepareMusic();
        musicTikTokBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "tiktok";
    }
    public void ActivateFiveBeat()
    {
        PrepareMusic();
        musicFiveBeatHeptagon.gameObject.SetActive(true);
        modeBeat = "five";
    }

    public void ActivateMemoryEasy()
    {
        PrepareMemory();
        memoryEasyHeptagon.gameObject.SetActive(true);
        modeMemory = "every action";
    }
    public void ActivateMemoryMedium()
    {
        PrepareMemory();
        memoryMediumHeptagon.gameObject.SetActive(true);
        modeMemory = "show all";
    }
    public void ActivateMemoryHard()
    {
        PrepareMemory();
        memoryHardHeptagon.gameObject.SetActive(true);
        modeMemory = "show one";
    }

    public void ActivatePhysicalSpeedAccuracy()
    {
        PreparePhysical();
        physicalSpeedAccuracyHeptagon.gameObject.SetActive(true);
        modeMotor = "speed accuracy";
    }

    public void ActivatePhysicalSpeedAccuracyHalfway()
    {
        PreparePhysical();
        physicalSpeedAccuracyHalfwayHeptagon.gameObject.SetActive(true);
        modeMotor = "speed accuracy halfway";
    }

    public void ActivatePhysicalSpeedAccuracyVisitAll()
    {
        PreparePhysical();
        physicalSpeedAccuracyVisitAllHeptagon.gameObject.SetActive(true);
        modeMotor = "visit all slots";
    }

    public void ActivateHeptagon()
    {
        if(heptagonHeptagon)
        {
            heptagonHeptagon.gameObject.SetActive(true);
        }
        
    }

    public void DimMaskVisual()
    {
        Color maskColor = maskVisualImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskVisualImage.color = maskColor;
    }
    public void DimMaskMath()
    {
        Color maskColor = maskMathImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMathImage.color = maskColor;
    }
    public void DimMaskPhysical()
    {
        Color maskColor = maskPhysicalImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskPhysicalImage.color = maskColor;
    }
    public void DimMaskMemory()
    {
        Color maskColor = maskMemoryImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMemoryImage.color = maskColor;
    }
    public void DimMaskMusic()
    {
        Color maskColor = maskMusicImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMusicImage.color = maskColor;
    }
    public void DimMaskVerbal()
    {
        Color maskColor = maskVerbalImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskVerbalImage.color = maskColor;
    }
    public void DimMaskSpatial()
    {
        Color maskColor = maskSpatialImage.color;
        maskColor.a = 0.2f;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskSpatialImage.color = maskColor;
    }

    public void UnselectAllButtons()
    {
        Color maskColor = maskVisualImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskVisualImage.color = maskColor;

        maskColor = maskMathImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMathImage.color = maskColor;

        maskColor = maskPhysicalImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskPhysicalImage.color = maskColor;

        maskColor = maskMemoryImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMemoryImage.color = maskColor;

        maskColor = maskMusicImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskMusicImage.color = maskColor;

        maskColor = maskVerbalImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskVerbalImage.color = maskColor;

        maskColor = maskSpatialImage.color;
        maskColor.r = 1f;
        maskColor.g = 1f;
        maskColor.b = 1f;
        maskSpatialImage.color = maskColor;
    }


    public void WorkoutHeptagonInfo(string modeNumber, string modeColor,
        string modeShape, string modeWord, string modeBeat, string modeMemory,
        string modeMotor)
    {

        if (modeNumber == "add")
        {
            ActivateMathAdd();
        }
        else if (modeNumber == "multiply")
        {
            ActivateMathMultiply();
        }
        else if (modeNumber == "gcd")
        {
            ActivateMathGcd();
        }
        else if (modeNumber == "vector")
        {
            ActivateMathVector();
        }
        else if (modeNumber == "interval")
        {
            ActivateMathInterval();
        }
        else if (modeNumber == "trigon")
        {
            ActivateMathTrigon();
        }
        else if (modeNumber == "sort")
        {
            ActivateMathSort();
        }



        if (modeColor == "add")
        {
            ActivateVisualAdd();
        }
        else if (modeColor == "subtract")
        {
            ActivateVisualSubtract();
        }
        else if (modeColor == "gray")
        {
            ActivateVisualGray();
        }
        else if (modeColor == "text")
        {
            ActivateVisualText();
        }



        if (modeShape == "triangle")
        {
            ActivateSpatialTriangle();
        }
        else if (modeShape == "rectangle")
        {
            ActivateSpatialRectangle();
        }
        else if (modeShape == "triple")
        {
            ActivateSpatialTriple();
        }
        else if (modeShape == "kanizsa")
        {
            ActivateSpatialKanizsa();
        }
        else if (modeShape == "sphere")
        {
            ActivateSpatialSphere();
        }
        else if (modeShape == "hanoi")
        {
            ActivateSpatialHanoi();
        }



        if (modeWord == "verbs")
        {
            ActivateVerbalVerbs();
        }
        else if (modeWord == "adjectives")
        {
            ActivateVerbalAdjectives();
        }
        else if (modeWord == "prepositions")
        {
            ActivateVerbalPrepositions();
        }
        else if (modeWord == "nouns")
        {
            ActivateVerbalNouns();
        }
        else if (modeWord == "synVerbs")
        {
            ActivateVerbalSynVerbs();
        }
        else if (modeWord == "synAdjectives")
        {
            ActivateVerbalSynAdjectives();
        }
        else if (modeWord == "grammar")
        {
            ActivateVerbalGrammar();
        }
        else if (modeWord == "questions")
        {
            ActivateVerbalQuestions();
        }
        else if (modeWord == "scrabble")
        {
            ActivateVerbalScrabble();
        }



        if (modeBeat == "double")
        {
            ActivateDoubleBeat();
        }
        else if (modeBeat == "single")
        {
            ActivateSingleBeat();
        }
        else if (modeBeat == "double fast")
        {
            ActivateDoubleFastBeat();
        }
        else if (modeBeat == "single fast")
        {
            ActivateSingleFastBeat();
        }
        else if (modeBeat == "tiktok")
        {
            ActivateTikTokBeat();
        }
        else if (modeBeat == "five")
        {
            ActivateFiveBeat();
        }



        if (modeMemory == "every action")
        {
            ActivateMemoryEasy();
        }
        else if (modeMemory == "show all")
        {
            ActivateMemoryMedium();
        }
        else if (modeMemory == "show one")
        {
            ActivateMemoryHard();
        }



        if (modeMotor == "speed accuracy")
        {
            ActivatePhysicalSpeedAccuracy();
        }
        else if (modeMotor == "speed accuracy halfway")
        {
            ActivatePhysicalSpeedAccuracyHalfway();
        }
        else if (modeMotor == "visit all slots")
        {
            ActivatePhysicalSpeedAccuracyVisitAll();
        }


    }


    public void HighlightMaskVisual()
    {
        UnselectAllButtons();
        
        if(cycleThrough && modeColor == null)
        {
            visualTextHeptagon.gameObject.SetActive(false);
            ActivateVisualAdd();
        }
        else if(cycleThrough && modeColor == "add")
        {
            visualAddHeptagon.gameObject.SetActive(false);
            ActivateVisualSubtract();
        }
        else if (cycleThrough && modeColor == "subtract")
        {
            visualSubtractHeptagon.gameObject.SetActive(false);
            ActivateVisualGray();
        }
        else if (cycleThrough && modeColor == "gray")
        {
            visualGrayHeptagon.gameObject.SetActive(false);
            ActivateVisualText();
        }
        else if(cycleThrough && modeColor == "text")
        {
            TurnOffVisual();
            if(modeNumber == null && modeColor == null && modeShape == null && modeWord == null)
            {
                TurnOffMemory();
            }
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskVisualImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskVisualImage.color = maskColor;

        SaveGame.Save<string>("modeColor", modeColor);
        IsValidSelection();

        if (modeColor == "add")
        {
            descriptionController.SetAddColorDescription();
        }
        else if (modeColor == "subtract")
        {
            descriptionController.SetSubtractColorDescription();
        }
        else if (modeColor == "gray")
        {
            descriptionController.SetGrayColorDescription();
        }
        else if (modeColor == "text")
        {
            descriptionController.SetTextColorDescription();
        }
    }

    public void HighlightMaskMath()
    {
        UnselectAllButtons();
        
        if (cycleThrough && modeNumber == null)
        {
            mathSortHeptagon.gameObject.SetActive(false);
            ActivateMathAdd();
        }
        else if (cycleThrough && modeNumber == "add")
        {
            mathAddHeptagon.gameObject.SetActive(false);
            ActivateMathMultiply();
        }
        else if (cycleThrough && modeNumber == "multiply")
        {
            mathMultiplyHeptagon.gameObject.SetActive(false);
            ActivateMathGcd();
        }
        else if (cycleThrough && modeNumber == "gcd")
        {
            mathGcdHeptagon.gameObject.SetActive(false);
            ActivateMathVector();
        }
        else if (cycleThrough && modeNumber == "vector")
        {
            mathVectorHeptagon.gameObject.SetActive(false);
            ActivateMathInterval();
        }
        else if (cycleThrough && modeNumber == "interval")
        {
            mathIntervalHeptagon.gameObject.SetActive(false);
            ActivateMathTrigon();
        }
        else if (cycleThrough && modeNumber == "trigon")
        {
            mathTrigonlHeptagon.gameObject.SetActive(false);
            ActivateMathSort();
        }
        else if (cycleThrough && modeNumber == "sort")
        {
            TurnOffMath();
            if (modeNumber == null && modeColor == null && modeShape == null && modeWord == null)
            {
                TurnOffMemory();
            }
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskMathImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskMathImage.color = maskColor;

        //Debug.Log(modeNumber);
        SaveGame.Save<string>("modeNumber", modeNumber);
        IsValidSelection();
        //Debug.Log(modeNumber);

        if (modeNumber == "add")
        {
            descriptionController.SetAddNumberDescription();
        }
        else if (modeNumber == "multiply")
        {
            descriptionController.SetMultiplyNumberDescription();
        }
        else if (modeNumber == "gcd")
        {
            descriptionController.SetGcdNumberDescription();
        }
        else if (modeNumber == "vector")
        {
            descriptionController.SetVectoreNumberDescription();
        }
        else if (modeNumber == "interval")
        {
            descriptionController.SetIntervalNumberDescription();
        }
        else if (modeNumber == "trigon")
        {
            descriptionController.SetTrigonNumberDescription();
        }
        else if (modeNumber == "sort")
        {
            descriptionController.SetSortNumberDescription();
        }
    }

    public void HighlightMaskPhysical()
    {
        UnselectAllButtons();

        if (cycleThrough && modeMotor == null)
        {
            TurnOffMusic(); //Mutually exclusive
            physicalSpeedAccuracyVisitAllHeptagon.gameObject.SetActive(false);
            ActivatePhysicalSpeedAccuracy();
        }
        else if (cycleThrough && modeMotor == "speed accuracy")
        {
            TurnOffMusic(); //Mutually exclusive
            physicalSpeedAccuracyHeptagon.gameObject.SetActive(false);
            ActivatePhysicalSpeedAccuracyHalfway();
        }
        else if (cycleThrough && modeMotor == "speed accuracy halfway")
        {
            TurnOffMusic(); //Mutually exclusive
            physicalSpeedAccuracyHalfwayHeptagon.gameObject.SetActive(false);
            ActivatePhysicalSpeedAccuracyVisitAll();
        }
        else if (cycleThrough && modeMotor == "visit all slots")
        {
            TurnOffPhysical();
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskPhysicalImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskPhysicalImage.color = maskColor;

        SaveGame.Save<string>("modeMotor", modeMotor);
        SaveGame.Save<string>("modeBeat", modeBeat);
        IsValidSelection();

        if (modeMotor == "speed accuracy")
        {
            descriptionController.SetOnSlotMotorDescription();
        }
        else if (modeMotor == "speed accuracy halfway")
        {
            descriptionController.SetHalfwaySlotMotorDescription();
        }
        else if (modeMotor == "visit all slots")
        {
            descriptionController.SetVisitAllMotorDescription();
        }
    }

    public void HighlightMaskMemory()
    {
        if(modeNumber != null || modeColor != null || modeShape != null || modeWord != null)
        {
            UnselectAllButtons();

            if (cycleThrough && modeMemory == null)
            {
                memoryHardHeptagon.gameObject.SetActive(false);
                ActivateMemoryEasy();
            }
            else if (cycleThrough && modeMemory == "every action")
            {
                memoryEasyHeptagon.gameObject.SetActive(false);
                ActivateMemoryMedium();
            }
            else if (cycleThrough && modeMemory == "show all")
            {
                memoryMediumHeptagon.gameObject.SetActive(false);
                ActivateMemoryHard();
            }
            else if (cycleThrough && modeMemory == "show one")
            {
                TurnOffMemory();
                descriptionController.HideDescriptions();
                descriptionController.SetAnyCombinationDescription();
            }

            Color maskColor = maskMemoryImage.color;
            maskColor.r = 1f;
            maskColor.g = 0.54f;
            maskColor.b = 0.54f;
            maskMemoryImage.color = maskColor;

            SaveGame.Save<string>("modeMemory", modeMemory);
            IsValidSelection();

            if (modeMemory == "every action")
            {
                descriptionController.SetEasyMemoryDescription();
            }
            else if (modeMemory == "show all")
            {
                descriptionController.SetMediumMemoryDescription();
            }
            else if (modeMemory == "show one")
            {
                descriptionController.SetHardMemoryDescription();
            }
        }
        
    }

    public void HighlightMaskMusic()
    {
        UnselectAllButtons();

        if (cycleThrough && modeBeat == null)
        {
            TurnOffPhysical(); //Mutually exclusive
            musicFiveBeatHeptagon.gameObject.SetActive(false);
            ActivateDoubleBeat();
        }
        else if (cycleThrough && modeBeat == "double")
        {
            TurnOffPhysical(); //Mutually exclusive
            musicDoubleBeatHeptagon.gameObject.SetActive(false);
            ActivateSingleBeat();
        }
        else if (cycleThrough && modeBeat == "single")
        {
            TurnOffPhysical(); //Mutually exclusive
            musicSingleBeatHeptagon.gameObject.SetActive(false);
            ActivateDoubleFastBeat();
        }
        else if (cycleThrough && modeBeat == "double fast")
        {
            TurnOffPhysical(); //Mutually exclusive
            musicDoubleFastBeatHeptagon.gameObject.SetActive(false);
            ActivateSingleFastBeat();
        }
        else if (cycleThrough && modeBeat == "single fast")
        {
            TurnOffPhysical(); //Mutually exclusive
            musicSingleFastBeatHeptagon.gameObject.SetActive(false);
            ActivateTikTokBeat();
        }
        else if (cycleThrough && modeBeat == "tiktok")
        {
            TurnOffPhysical(); //Mutually exclusive
            musicTikTokBeatHeptagon.gameObject.SetActive(false);
            ActivateFiveBeat();
        }
        else if (cycleThrough && modeBeat == "five")
        {
            TurnOffMusic(); 
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskMusicImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskMusicImage.color = maskColor;

        SaveGame.Save<string>("modeBeat", modeBeat);
        SaveGame.Save<string>("modeMotor", modeMotor);

        IsValidSelection();

        if (modeBeat == "double")
        {
            descriptionController.SetDoubleBeatDescription();
        }
        else if (modeBeat == "single")
        {
            descriptionController.SetSingleBeatDescription();
        }
        else if (modeBeat == "double fast")
        {
            descriptionController.SetDoubleFastBeatDescription();
        }
        else if (modeBeat == "single fast")
        {
            descriptionController.SetSingleFastBeatDescription();
        }
        else if (modeBeat == "tiktok")
        {
            descriptionController.SetTikTokBeatDescription();
        }
        else if (modeBeat == "five")
        {
            descriptionController.SetFiveBeatDescription();
        }

    }

    public void HighlightMaskVerbal()
    {
        UnselectAllButtons();

        if (cycleThrough && modeWord == null)
        {
            verbalScrabbleHeptagon.gameObject.SetActive(false);
            ActivateVerbalVerbs();
        }
        else if (cycleThrough && modeWord == "verbs")
        {
            verbalVerbsHeptagon.gameObject.SetActive(false);
            ActivateVerbalAdjectives();
        }
        else if (cycleThrough && modeWord == "adjectives")
        {
            verbalAdjectivesHeptagon.gameObject.SetActive(false);
            ActivateVerbalNouns();
        }
        //else if (cycleThrough && modeWord == "prepositions")
        //{
        //    verbalPrepositionsHeptagon.gameObject.SetActive(false);
        //    ActivateVerbalNouns();
        //}
        else if (cycleThrough && modeWord == "nouns")
        {
            verbalNounsHeptagon.gameObject.SetActive(false);
            ActivateVerbalSynVerbs();
        }
        else if (cycleThrough && modeWord == "synVerbs")
        {
            verbalSynVerbsHeptagon.gameObject.SetActive(false);
            ActivateVerbalSynAdjectives();
        }
        else if (cycleThrough && modeWord == "synAdjectives")
        {
            verbalSynAdjectivesHeptagon.gameObject.SetActive(false);
            ActivateVerbalGrammar();
        }
        else if (cycleThrough && modeWord == "grammar")
        {
            verbalGrammarHeptagon.gameObject.SetActive(false);
            ActivateVerbalQuestions();
        }
        else if (cycleThrough && modeWord == "questions")
        {
            verbalQuestionsHeptagon.gameObject.SetActive(false);
            ActivateVerbalScrabble();
        }
        else if (cycleThrough && modeWord == "scrabble")
        {
            TurnOffVerbal();
            if (modeNumber == null && modeColor == null && modeShape == null && modeWord == null)
            {
                TurnOffMemory();
            }
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskVerbalImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskVerbalImage.color = maskColor;

        SaveGame.Save<string>("modeWord", modeWord);
        IsValidSelection();

        if (modeWord == "verbs")
        {
            descriptionController.SetSubtractVerbsDescription();
        }
        else if(modeWord == "adjectives")
        {
            descriptionController.SetSubtractAdjectivesDescription();
        }
        else if (modeWord == "prepositions")
        {
            descriptionController.SetSubtractPrepositionsDescription();
        }
        else if (modeWord == "nouns")
        {
            descriptionController.SetSubtractNounsDescription();
        }
        else if (modeWord == "synVerbs")
        {
            descriptionController.SetSubtractSynVerbsDescription();
        }
        else if (modeWord == "synAdjectives")
        {
            descriptionController.SetSubtractSynAdjectivesDescription();
        }
        else if (modeWord == "grammar")
        {
            descriptionController.SetSubtractGrammarDescription();
        }
        else if (modeWord == "questions")
        {
            descriptionController.SetSubtractQuestionsDescription();
        }
        else if (modeWord == "scrabble")
        {
            descriptionController.SetScrabbleDescription();
        }
    }

    public void HighlightMaskSpatial()
    {
        UnselectAllButtons();

        if (cycleThrough && modeShape == null)
        {
            spatiaHanoiHeptagon.gameObject.SetActive(false);
            ActivateSpatialTriangle();
        }
        else if (cycleThrough && modeShape == "triangle")
        {
            spatialTriangleHeptagon.gameObject.SetActive(false);
            ActivateSpatialRectangle();
        }
        else if (cycleThrough && modeShape == "rectangle")
        {
            spatialRectangleHeptagon.gameObject.SetActive(false);
            ActivateSpatialTriple();
        }
        else if (cycleThrough && modeShape == "triple")
        {
            spatialTripleHeptagon.gameObject.SetActive(false);
            ActivateSpatialKanizsa();
        }
        else if (cycleThrough && modeShape == "kanizsa")
        {
            spatialKanizsaHeptagon.gameObject.SetActive(false);
            ActivateSpatialSphere();
        }
        else if (cycleThrough && modeShape == "sphere")
        {
            spatialSphereHeptagon.gameObject.SetActive(false);
            ActivateSpatialHanoi();
        }
        else if (cycleThrough && modeShape == "hanoi")
        {
            TurnOffSpatial();
            if (modeNumber == null && modeColor == null && modeShape == null && modeWord == null)
            {
                TurnOffMemory();
            }
            descriptionController.HideDescriptions();
            descriptionController.SetAnyCombinationDescription();
        }

        Color maskColor = maskSpatialImage.color;
        maskColor.r = 1f;
        maskColor.g = 0.54f;
        maskColor.b = 0.54f;
        maskSpatialImage.color = maskColor;

        SaveGame.Save<string>("modeShape", modeShape);
        IsValidSelection();

        if (modeShape == "triangle")
        {
            descriptionController.SetShapeTriangleDescription();
        }
        else if (modeShape == "rectangle")
        {
            descriptionController.SetShapeSquareDescription();
        }
        else if (modeShape == "triple")
        {
            descriptionController.SetShapeTripleDescription();
        }
        else if (modeShape == "kanizsa")
        {
            descriptionController.SetShapeKanizsaDescription();
        }
        else if (modeShape == "sphere")
        {
            descriptionController.SetShapeSphereDescription();
        }
        else if (modeShape == "hanoi")
        {
            descriptionController.SetShapeHanoiDescription();
        }
    }

    public void ActivateButtonVisual()
    {
        buttonVisualHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonMath()
    {
        buttonMathHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonPhysical()
    {
        buttonPhysicalHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonMemory()
    {
        buttonMemoryHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonMusic()
    {
        buttonMusicHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonVerbal()
    {
        buttonVerbalHeptagon.gameObject.SetActive(true);
    }
    public void ActivateButtonSpatial()
    {
        buttonSpatialHeptagon.gameObject.SetActive(true);
        buttonSpatialHeptagon2.gameObject.SetActive(true);
        buttonSpatialHeptagon3.gameObject.SetActive(true);
        buttonSpatialHeptagon4.gameObject.SetActive(true);
    }


}
