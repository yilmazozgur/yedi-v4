using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using BayatGames.SaveGameFree;

public class LevelController : MonoBehaviour {

    float waitToLoad = 1f;
    int numberOfCards = 0;
    bool levelTimerFinished = false;
    public bool gameFinished = false;
    bool rewardedAdWatched = false;
    int numberOfRewardedAdsWatched;
    ManaDisplay manaDisplay;
    StatsControllerExpanded statsControllerExpanded;
    StatsCollectorExpanded statsCollectorExpanded;
    public int selectedLevel;
    BuyCardButton card1DNumber;
    BuyCardButton card1DColor;
    BuyCardButton card1DShape;
    BuyCardButton card1DWord;
    BuyCardButton card1DMusic;
    BuyCardButton card1DMemory;
    BuyCardButton card1DPhysical;
    //BuyCardButton card4D;
    BuyCardButton cardAny;
    BeatGenerator beatGenerator;
    public bool numberActive = false;
    public bool colorActive = false;
    public bool shapeActive = false;
    public bool wordActive = false;
    public bool beatActive = false;
    public bool memoryActive = false;
    public bool motorActive = false;
    CardDrawer cardDrawer;
    public bool gamePaused = false;
    GameTimer gameTimer;
    LevelCompleteCanvas winLabel;
    Canvas winLabelCanvas;
    Canvas mainCanvasCanvas;
    HeptagonController heptagonController;
    Tutorial tutorial;
    TutorialController tutorialController;
    SevenMinuteController sevenMinuteController;
    ContinueButton continueButton;

    string modeNumber = null;
    string modeColor = null;
    string modeShape = null;
    string modeWord = null;
    string modeBeat = null;
    string modeMemory = null;
    string modeMotor = null;
    bool doubleTime = false;

    float cardTypeAnyCombination;

    TextAsset wordsDictResource;
    Dictionary<string, int> wordDictionary = new Dictionary<string, int>();
    AdsControllerYedi adsControllerYedi;
    LevelLoader levelLoader;

    private void Start()
    {
        SaveGame.Save<int>("numberOfRewardedAdsWatched", 0);
        gamePaused = false;
        SaveGame.Save<bool>("gamePaused", false);
        SaveGame.Save<bool>("levelTimerFinished", false);

        //gameFinished = false;
        wordsDictResource = (TextAsset)Resources.Load("wordlist");
        string[] wordsDict = wordsDictResource.text.Split("\n"[0]); ;
        //Dictionary filled with common words (3000 of them)
        string line_iter;
        foreach (string line in wordsDict)
        {
            line_iter = line.Replace("\n", "");
            line_iter = line_iter.Replace("\r", "");
            line_iter = line_iter.Replace("\t", "");
            wordDictionary.Add(line_iter, line_iter.Length);
        }
        //Debug.Log(wordDictionary.Count);

        cardDrawer = FindAnyObjectByType<CardDrawer>();
        heptagonController = FindAnyObjectByType<HeptagonController>();
        statsControllerExpanded = FindAnyObjectByType<StatsControllerExpanded>();
        winLabel = FindAnyObjectByType<LevelCompleteCanvas>();
        tutorial = FindAnyObjectByType<Tutorial>();
        sevenMinuteController = FindAnyObjectByType<SevenMinuteController>();
        levelLoader = FindAnyObjectByType<LevelLoader>();
        continueButton = FindAnyObjectByType<ContinueButton>();

        winLabelCanvas = winLabel.GetComponent<Canvas>();
        winLabelCanvas.enabled = false;
        mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
        manaDisplay = FindAnyObjectByType<ManaDisplay>();
        beatGenerator = FindAnyObjectByType<BeatGenerator>();
        gameTimer = FindAnyObjectByType<GameTimer>();
        statsCollectorExpanded = FindAnyObjectByType<StatsCollectorExpanded>();

        selectedLevel = SaveGame.Load<int>("selectedLevel");
        BuyCardButton[] buyCardButtonList = FindObjectsByType<BuyCardButton>(FindObjectsSortMode.None);
        foreach (BuyCardButton cardButton in buyCardButtonList)
        {
            if(cardButton.gameObject.name == "Card1DNumber")
            {
                card1DNumber = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DColor")
            {
                card1DColor = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DShape")
            {
                card1DShape = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DWord")
            {
                card1DWord = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DMusic")
            {
                card1DMusic = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DMemory")
            {
                card1DMemory = cardButton;
            }
            if (cardButton.gameObject.name == "Card1DPhysical")
            {
                card1DPhysical = cardButton;
            }
            //else if (cardButton.gameObject.name == "Card4D")
            //{
            //    card4D = cardButton;
            //}
            else if (cardButton.gameObject.name == "CardAny")
            {
                cardAny = cardButton;
            }
        }

        tutorial.gameObject.SetActive(false);

        LoadModes();
        SetLevelParameters();
        SaveModes();

        statsCollectorExpanded.FlushCurrentGameData();
        gameTimer.SetTime();

        adsControllerYedi = FindAnyObjectByType<AdsControllerYedi>();
        if (adsControllerYedi != null)
        {
            adsControllerYedi.ShowInterstitialAd();
        }

    }

    public bool DictionaryWordLookup(string newWord)
    {
        bool keyExists = wordDictionary.ContainsKey(newWord);
        //Debug.Log(wordDictionary["sit"]);
        return keyExists;
    }

    private void LoadModes()
    {
        modeNumber = SaveGame.Load<string>("modeNumber");
        modeColor = SaveGame.Load<string>("modeColor");
        modeShape = SaveGame.Load<string>("modeShape");
        modeWord = SaveGame.Load<string>("modeWord");
        modeBeat = SaveGame.Load<string>("modeBeat");
        modeMemory = SaveGame.Load<string>("modeMemory");
        modeMotor = SaveGame.Load<string>("modeMotor");
    }

    private void SaveModes()
    {
        SaveGame.Save<string>("modeNumber", modeNumber);
        SaveGame.Save<string>("modeColor", modeColor);
        SaveGame.Save<string>("modeShape", modeShape);
        SaveGame.Save<string>("modeWord", modeWord);
        SaveGame.Save<string>("modeBeat", modeBeat);
        SaveGame.Save<string>("modeMemory", modeMemory);
        SaveGame.Save<string>("modeMotor", modeMotor);
    }

    public void WorkoutGameUsedUp()
    {
        if (selectedLevel == 100)
        {
            sevenMinuteController.gamePlayed();
        }
    }

    private void SetLevelParameters()
    {
        if(selectedLevel == 0)
        {
            card1DNumber.disabled = false;
            card1DNumber.enableByDefaultEffects = true;
            card1DColor.disabled = false;
            card1DColor.enableByDefaultEffects = true;
            card1DShape.disabled = false;
            card1DShape.enableByDefaultEffects = true;
            card1DWord.disabled = false;
            card1DWord.enableByDefaultEffects = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 4;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            modeNumber = "add";
            modeColor = "add";
            modeShape = "triangle";
            modeWord = "verbs";
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;

            tutorial.gameObject.SetActive(true);
            tutorialController = FindAnyObjectByType<TutorialController>();
            if(tutorialController)
            {
                tutorialController.InitiateTutorial();
            }
            
        }
        else if (selectedLevel == 1) //Only number, add
        {
            card1DNumber.disabled = false;
            card1DNumber.enableByDefaultEffects = true;

            card1DColor.disabled = true;
            card1DShape.disabled = true;
            card1DWord.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 5;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = true;
            colorActive = false;
            shapeActive = false;
            wordActive = false;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            modeNumber = "add";
            modeColor = null;
            modeShape = null;
            modeWord = null;
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;
        }
        else if(selectedLevel == 2) //Only color, add
        {
            card1DColor.disabled = false;
            card1DColor.enableByDefaultEffects = true;

            card1DNumber.disabled = true;
            card1DShape.disabled = true;
            card1DWord.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 6;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = false;
            colorActive = true;
            shapeActive = false;
            wordActive = false;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            modeNumber = null;
            modeColor = "add";
            modeShape = null;
            modeWord = null;
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;
        }
        else if (selectedLevel == 3) //Only shape, triangle
        {
            card1DShape.disabled = false;
            card1DShape.enableByDefaultEffects = true;

            card1DNumber.disabled = true;
            card1DColor.disabled = true;
            card1DWord.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 7;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = false;
            colorActive = false;
            shapeActive = true;
            wordActive = false;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            modeNumber = null;
            modeColor = null;
            modeShape = "triangle";
            modeWord = null;
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;
            
        }
        else if (selectedLevel == 4) //Only word, verbs
        {
            card1DWord.disabled = false;
            card1DWord.enableByDefaultEffects = true;

            card1DNumber.disabled = true;
            card1DColor.disabled = true;
            card1DShape.disabled = true;
            //card4D.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 8;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = false;
            colorActive = false;
            shapeActive = false;
            wordActive = true;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            
            modeNumber = null;
            modeColor = null;
            modeShape = null;
            modeWord = "verbs";
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;
        }
        else if (selectedLevel == 5) //All of above
        {
            card1DNumber.disabled = false;
            card1DNumber.enableByDefaultEffects = true;
            card1DColor.disabled = false;
            card1DColor.enableByDefaultEffects = true;
            card1DShape.disabled = false;
            card1DShape.enableByDefaultEffects = true;
            card1DWord.disabled = false;
            card1DWord.enableByDefaultEffects = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 2222000;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
            beatActive = false;
            memoryActive = false;
            motorActive = false;

            modeNumber = "add";
            modeColor = "add";
            modeShape = "triangle";
            modeWord = "verbs";
            modeBeat = null;
            modeMemory = null;
            modeMotor = null;
        }
        
        else if (selectedLevel == 6) //"Beat Only" Level, Double beat
        {
            beatGenerator.SetBeatActivated(true);

            card1DNumber.disabled = true;
            card1DColor.disabled = true;
            card1DShape.disabled = true;
            card1DWord.disabled = true;
            //card4D.disabled = true;

            card1DMemory.disabled = true;
            card1DPhysical.disabled = true;

            card1DMusic.disabled = false;
            card1DMusic.enableByDefaultEffects = true;

            cardAny.cardType = 1111211;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = false;
            colorActive = false;
            shapeActive = false;
            wordActive = false;
            beatActive = true;
            memoryActive = false;
            motorActive = false;

            modeNumber = null;
            modeColor = null;
            modeShape = null;
            modeWord = null;
            modeBeat = "double";
            modeMemory = null;
            modeMotor = null;
            
        }

        else if (selectedLevel == 7) //Number + Memory level
        {
            card1DNumber.disabled = false;
            card1DNumber.enableByDefaultEffects = true;

            card1DColor.disabled = true;
            card1DShape.disabled = true;
            card1DWord.disabled = true;
            //card4D.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = false;
            card1DMemory.enableByDefaultEffects = true;
            card1DPhysical.disabled = true;

            cardAny.cardType = 2111121;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = true;
            colorActive = false;
            shapeActive = false;
            wordActive = false;
            beatActive = false;
            memoryActive = true;
            motorActive = false;

            modeNumber = "add";
            modeColor = null;
            modeShape = null;
            modeWord = null;
            modeBeat = null;
            modeMemory = "show all";
            modeMotor = null;
        }

        else if (selectedLevel == 8) //Motor level
        {
            card1DNumber.disabled = true;
            card1DColor.disabled = true;
            card1DShape.disabled = true;
            card1DWord.disabled = true;
            //card4D.disabled = true;

            card1DMusic.disabled = true;
            card1DMemory.disabled = true;
            card1DPhysical.disabled = false;
            card1DPhysical.enableByDefaultEffects = true;

            cardAny.cardType = 1111112;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;

            numberActive = false;
            colorActive = false;
            shapeActive = false;
            wordActive = false;
            beatActive = false;
            memoryActive = false;
            motorActive = true;

            modeNumber = null;
            modeColor = null;
            modeShape = null;
            modeWord = null;
            modeBeat = null;
            modeMemory = null;
            modeMotor = "speed accuracy";
        }


        else if (selectedLevel == 9 || selectedLevel == 100) //Any combination. Read from user selection
        {
           
            //card4D.disabled = true;

            if (modeNumber == null)
            {
                //Debug.Log("No number");
                card1DNumber.disabled = true;
                numberActive = false;
                cardTypeAnyCombination = 1000000;
            }
            else if(modeNumber == "add")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 2000000;
            }
            else if (modeNumber == "multiply")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 3000000;
            }
            else if (modeNumber == "gcd")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 4000000;
            }
            else if (modeNumber == "vector")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 5000000;
            }
            else if (modeNumber == "interval")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 6000000;
            }
            else if (modeNumber == "trigon")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 7000000;
            }
            else if (modeNumber == "sort")
            {
                card1DNumber.disabled = false;
                card1DNumber.enableByDefaultEffects = true;
                numberActive = true;
                cardTypeAnyCombination = 8000000;
            }


            if (modeColor == null)
            {
                card1DColor.disabled = true;
                colorActive = false;
                cardTypeAnyCombination += 100000;
            }
            else if (modeColor == "add")
            {
                card1DColor.disabled = false;
                card1DColor.enableByDefaultEffects = true;
                colorActive = true;
                cardTypeAnyCombination += 200000;
            }
            else if (modeColor == "subtract")
            {
                card1DColor.disabled = false;
                card1DColor.enableByDefaultEffects = true;
                colorActive = true;
                cardTypeAnyCombination += 300000;
            }
            else if (modeColor == "gray")
            {
                card1DColor.disabled = false;
                card1DColor.enableByDefaultEffects = true;
                colorActive = true;
                cardTypeAnyCombination += 400000;
            }
            else if (modeColor == "text")
            {
                card1DColor.disabled = false;
                card1DColor.enableByDefaultEffects = true;
                colorActive = true;
                cardTypeAnyCombination += 500000;
            }

            if (modeShape == null)
            {
                card1DShape.disabled = true;
                shapeActive = false;
                cardTypeAnyCombination += 10000;
            }
            else if (modeShape == "triangle")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 20000;
            }
            else if (modeShape == "rectangle")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 30000;
            }
            else if (modeShape == "triple")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 40000;
            }
            else if (modeShape == "kanizsa")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 50000;
            }
            else if (modeShape == "sphere")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 60000;
            }
            else if (modeShape == "hanoi")
            {
                card1DShape.disabled = false;
                card1DShape.enableByDefaultEffects = true;
                shapeActive = true;
                cardTypeAnyCombination += 70000;
                //Double the time for hard game hanoi
                doubleTime = true;
            }

            if (modeWord == null)
            {
                card1DWord.disabled = true;
                wordActive = false;
                cardTypeAnyCombination += 1000;
            }
            else if (modeWord == "verbs")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 2000;
            }
            else if (modeWord == "adjectives")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 3000;
            }
            //else if (modeWord == "prepositions")
            //{
            //    card1DWord.disabled = false;
            //    card1DWord.enableByDefaultEffects = true;
            //    wordActive = true;
            //    cardTypeAnyCombination += 4000;
            //}
            else if (modeWord == "nouns")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 4000;
            }
            else if (modeWord == "synVerbs")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 5000;
            }
            else if (modeWord == "synAdjectives")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 6000;
            }
            else if (modeWord == "grammar")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 7000;
            }
            else if (modeWord == "questions")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 8000;
            }
            else if (modeWord == "scrabble")
            {
                card1DWord.disabled = false;
                card1DWord.enableByDefaultEffects = true;
                wordActive = true;
                cardTypeAnyCombination += 9000;
                //Double the time for hard game scrabble
                doubleTime = true;
            }


            if (modeBeat == null)
            {
                card1DMusic.disabled = true;
                beatActive = false;
                cardTypeAnyCombination += 100;
            }
            else if (modeBeat == "double")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 200;
            }
            else if (modeBeat == "single")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 300;
            }
            else if (modeBeat == "double fast")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 400;
            }
            else if (modeBeat == "single fast")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 500;
            }
            else if (modeBeat == "tiktok")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 600;
            }
            else if (modeBeat == "five")
            {
                card1DMusic.disabled = false;
                card1DMusic.enableByDefaultEffects = true;
                beatGenerator.SetBeatActivated(true);
                beatActive = true;
                cardTypeAnyCombination += 700;
            }

            if (modeMemory == null)
            {
                card1DMemory.disabled = true;
                memoryActive = false;
                cardTypeAnyCombination += 10;
            }
            else if (modeMemory == "every action")
            {
                card1DMemory.disabled = false;
                card1DMemory.enableByDefaultEffects = true;
                memoryActive = true;
                cardTypeAnyCombination += 20;
            }
            else if (modeMemory == "show all")
            {
                card1DMemory.disabled = false;
                card1DMemory.enableByDefaultEffects = true;
                memoryActive = true;
                cardTypeAnyCombination += 30;
            }
            else if (modeMemory == "show one")
            {
                card1DMemory.disabled = false;
                card1DMemory.enableByDefaultEffects = true;
                memoryActive = true;
                cardTypeAnyCombination += 40;
            }

            if (modeMotor == null)
            {
                card1DPhysical.disabled = true;
                motorActive = false;
                cardTypeAnyCombination += 1;
            }
            else if (modeMotor == "speed accuracy")
            {
                card1DPhysical.disabled = false;
                card1DPhysical.enableByDefaultEffects = true;
                motorActive = true;
                cardTypeAnyCombination += 2;
            }
            else if (modeMotor == "speed accuracy halfway")
            {
                card1DPhysical.disabled = false;
                card1DPhysical.enableByDefaultEffects = true;
                motorActive = true;
                cardTypeAnyCombination += 3;
            }
            else if (modeMotor == "visit all slots")
            {
                card1DPhysical.disabled = false;
                card1DPhysical.enableByDefaultEffects = true;
                motorActive = true;
                cardTypeAnyCombination += 4;
            }

            cardAny.cardType = cardTypeAnyCombination;
            cardAny.disabled = false;
            cardAny.anyCardButton = true;
            cardAny.enableByDefault = true;
            
        }

        SaveGame.Save<bool>("doubleTime", doubleTime);
    }

    public void CardDrawn()
    {
        numberOfCards++;
    }

    public void CardSold()
    {
        numberOfCards--;
    }

    public void RewardedAdBool(bool watchedReward)
    {
        rewardedAdWatched = watchedReward;
    }

    public void ReturnFromRewardedAd()
    {
        gameTimer = FindAnyObjectByType<GameTimer>();
        gameTimer.gamePaused = false;
        gamePaused = false;
        SaveGame.Save<bool>("gamePaused", false);


        winLabel = FindAnyObjectByType<LevelCompleteCanvas>();
        winLabelCanvas = winLabel.GetComponent<Canvas>();
        winLabelCanvas.enabled = false;

        mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
        mainCanvasCanvas.enabled = true;

        cardDrawer = FindAnyObjectByType<CardDrawer>();
        if (cardDrawer)
        {
            cardDrawer.haltCardDraw = false;
        }
    }

    public bool ReturnGamePaused()
    {
        gamePaused = SaveGame.Load<bool>("gamePaused");
        return gamePaused;
    }

    public void IncrementRewardedNumber()
    {
        
        rewardedAdWatched = true;
        numberOfRewardedAdsWatched = SaveGame.Load<int>("numberOfRewardedAdsWatched");
        //Debug.Log(numberOfRewardedAdsWatched);
        numberOfRewardedAdsWatched += 1;
        SaveGame.Save<int>("numberOfRewardedAdsWatched", numberOfRewardedAdsWatched);
        //Debug.Log(numberOfRewardedAdsWatched);
    }

    public void BackButtonPressed()
    {
        DestroyGame();
        levelLoader = FindAnyObjectByType<LevelLoader>();
        levelLoader.LoadSceneSelection();
    }

    public void PauseGame()
    {
        gameTimer = FindAnyObjectByType<GameTimer>();
        numberOfRewardedAdsWatched = SaveGame.Load<int>("numberOfRewardedAdsWatched");
        gamePaused = SaveGame.Load<bool>("gamePaused");
        //Debug.Log(gamePaused);

        if (gameTimer.ReturnTimerFinished() == true && numberOfRewardedAdsWatched < 2)
        {
            //Debug.Log("Game finished");
            adsControllerYedi = FindAnyObjectByType<AdsControllerYedi>();
            if (adsControllerYedi != null)
            {
                gamePaused = true;
                SaveGame.Save<bool>("gamePaused", true);
                adsControllerYedi.ShowRewardedAd();
            }
            return;
        }
        if (gameTimer.ReturnTimerFinished() == true && numberOfRewardedAdsWatched >= 2)
        {
            BackButtonPressed();
        }


        if (gamePaused == false)
        {
            gameTimer = FindAnyObjectByType<GameTimer>();
            gameTimer.gamePaused = true;
            gamePaused = true;
            SaveGame.Save<bool>("gamePaused", true);

            mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
            mainCanvasCanvas.enabled = false;

            winLabel = FindAnyObjectByType<LevelCompleteCanvas>();
            winLabelCanvas = winLabel.GetComponent<Canvas>();
            winLabelCanvas.enabled = true;

            cardDrawer = FindAnyObjectByType<CardDrawer>();
            if (cardDrawer)
            {
                cardDrawer.haltCardDraw = true;
            }   
        }
        else
        {
            gameTimer = FindAnyObjectByType<GameTimer>();
            gameTimer.gamePaused = false;
            gamePaused = false;
            SaveGame.Save<bool>("gamePaused", false);

            winLabel = FindAnyObjectByType<LevelCompleteCanvas>();
            winLabelCanvas = winLabel.GetComponent<Canvas>();
            winLabelCanvas.enabled = false;

            mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
            mainCanvasCanvas.enabled = true;

            cardDrawer = FindAnyObjectByType<CardDrawer>();
            if(cardDrawer)
            {
                cardDrawer.haltCardDraw = false;
            }
            
        }
        
    }

    public void ContinueFromHelp()
    {
        if (gameTimer.ReturnTimerFinished() == true)
        {
            return;
        }

        gameTimer = FindAnyObjectByType<GameTimer>();
        gameTimer.gamePaused = false;
        gamePaused = false;
        SaveGame.Save<bool>("gamePaused", false);

        mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
        mainCanvasCanvas.enabled = true;

        cardDrawer = FindAnyObjectByType<CardDrawer>();
        cardDrawer.haltCardDraw = false;

        heptagonController.HeptagonHideHelp();
    }

    public void ShowHelp()
    {
        //gameTimer = FindAnyObjectByType<GameTimer>();
        //if (gameTimer.ReturnTimerFinished() == true)
        //{
        //    return;
        //}
        gamePaused = SaveGame.Load<bool>("gamePaused");
        if (gamePaused == false)
        {
            gameTimer = FindAnyObjectByType<GameTimer>();
            gameTimer.gamePaused = true;
            gamePaused = true;
            SaveGame.Save<bool>("gamePaused", true);

            mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
            mainCanvasCanvas.enabled = false;

            cardDrawer = FindAnyObjectByType<CardDrawer>();
            if (cardDrawer)
            {
                cardDrawer.haltCardDraw = true;
            }
                

            heptagonController = FindAnyObjectByType<HeptagonController>();
            if(heptagonController != null)
            {
                heptagonController.HeptagonShowHelp();
            }
            
        }
        else
        {
            gameTimer = FindAnyObjectByType<GameTimer>();
            gameTimer.gamePaused = false;
            gamePaused = false;
            SaveGame.Save<bool>("gamePaused", false);

            mainCanvasCanvas = FindAnyObjectByType<MainCanvas>().GetComponent<Canvas>();
            mainCanvasCanvas.enabled = true;

            cardDrawer = FindAnyObjectByType<CardDrawer>();
            if (cardDrawer)
            {
                cardDrawer.haltCardDraw = false;
            }

            heptagonController = FindAnyObjectByType<HeptagonController>();
            if (heptagonController != null)
            {
                heptagonController.HeptagonHideHelp();
            }
            
        }
        
    }

    IEnumerator HandleWinCondition()
    {
        winLabelCanvas.enabled = true;
        beatGenerator.StopBeat();
        //GetComponent<AudioSource>().Play();
        yield return new WaitForSeconds(waitToLoad);
    }


    public void LevelTimerFinished()
    {
        levelTimerFinished = true;
        SaveGame.Save<bool>("levelTimerFinished", true);
        gameFinished = gameTimer.ReturnTimerFinished();
        StartCoroutine(ShowWinLabel());
        //DestroyGame();

    }

    IEnumerator ShowWinLabel()
    {
        gamePaused = true;
        SaveGame.Save<bool>("gamePaused", true);
        winLabelCanvas.enabled = true;
        yield return new WaitForSeconds(waitToLoad);
    }

    //public void LevelTimerFinished()
    //{
    //    levelTimerFinished = true;
    //    gameFinished = gameTimer.ReturnTimerFinished();

    //    StopCardDealing();

    //    Card[] cardFinished = FindObjectsByType<Card>(FindObjectsSortMode.None);
    //    foreach(Card cardIter in cardFinished)
    //    {
    //        Destroy(cardIter);
    //    }
    //}

    void DestroyGame()
    {
        levelTimerFinished = SaveGame.Load<bool>("levelTimerFinished");
        //yield return new WaitForSeconds(waitToLoad);
        Debug.Log(levelTimerFinished);
        statsControllerExpanded = FindAnyObjectByType<StatsControllerExpanded>();
        beatGenerator = FindAnyObjectByType<BeatGenerator>();
        if (levelTimerFinished == true)
        {
            Debug.Log("Stats saved.");
            statsControllerExpanded.SaveGameStats();
        }
        
        Destroy(cardDrawer);
        
        beatGenerator.StopBeat();
        gameTimer.triggeredLevelFinished = true;

        Card[] cardFinished = FindObjectsByType<Card>(FindObjectsSortMode.None);
        foreach (Card cardIter in cardFinished)
        {
            Destroy(cardIter);
        }
    }

    public void StopCardDealing()
    {
        gameFinished = gameTimer.ReturnTimerFinished();
        
        Destroy(cardDrawer);
        
        StartCoroutine(HandleWinCondition());

        statsControllerExpanded.SaveGameStats();
    }

}
