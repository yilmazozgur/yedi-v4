using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using BayatGames.SaveGameFree;

public class TutorialController : MonoBehaviour
{
    public static TutorialController Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    public bool tutorialInitiated = false;
    public bool halted = false;

    public bool buyCard = false;
    public bool moveCardSlots = false;
    public bool buyAnotherCard = false;
    public bool mergeTwoCards = false;
    public bool mergeGains = false;
    public bool goal = false;
    public bool games = false;
    public bool sellcard = false;
    public bool cardValue = false;
    public bool timer = false;
    public bool dimensions = false;
    public bool otherDimensions = false;
    public bool helpPause = false;
    public bool stats = false;

    TutorialPopup[] tutorialPopups;
    Canvas buyCardPopup;
    Canvas moveCardSlotsPopup;
    Canvas buyAnotherCardPopup;
    Canvas mergeTwoCardsPopup;
    Canvas mergeGainsPopup;
    Canvas goalPopup;
    Canvas gamesPopup;
    Canvas sellcardPopup;
    Canvas cardValuePopup;
    Canvas timerPopup;
    Canvas dimensionsPopup;
    Canvas otherDimensionsPopup;
    Canvas helpPausePopup;
    Canvas statsPopup;

    LevelLoader levelLoader;


    // Start is called before the first frame update
    void Start()
    {
        levelLoader = LevelLoader.Instance;
        DeactivateAllTutorialPopups();
    }

    // Update is called once per frame
    void Update()
    {
        if(tutorialInitiated && !halted)
        {
            if(buyCard == false)
            {
                halted = true;
                buyCard = true;
                StartCoroutine(InitiatePopUp(buyCardPopup,3f));
                return;
            }
            if (moveCardSlots == false && buyCard == true)
            {
                halted = true;
                moveCardSlots = true;
                StartCoroutine(InitiatePopUp(moveCardSlotsPopup, 2f));
                return;
            }
            if (buyAnotherCard == false && buyCard == true && moveCardSlots == true)
            {
                halted = true;
                buyAnotherCard = true;
                StartCoroutine(InitiatePopUp(buyAnotherCardPopup, 2f));
                return;
            }
            if (mergeTwoCards == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true)
            {
                halted = true;
                mergeTwoCards = true;
                StartCoroutine(InitiatePopUp(mergeTwoCardsPopup, 2f));
                return;
            }
            if (mergeGains == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true)
            {
                halted = true;
                mergeGains = true;
                StartCoroutine(InitiatePopUp(mergeGainsPopup, 2f));
                return;
            }
            if (goal == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true)
            {
                halted = true;
                goal = true;
                StartCoroutine(InitiatePopUp(goalPopup, 2f));
                return;
            }
            if (games == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal ==true)
            {
                halted = true;
                games = true;
                StartCoroutine(InitiatePopUp(gamesPopup, 2f));
                return;
            }
            if (sellcard == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games ==true)
            {
                halted = true;
                sellcard = true;
                StartCoroutine(InitiatePopUp(sellcardPopup, 2f));
                return;
            }
            if (cardValue == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true)
            {
                halted = true;
                cardValue = true;
                StartCoroutine(InitiatePopUp(cardValuePopup, 2f));
                return;
            }
            if (timer == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true && cardValue == true)
            {
                halted = true;
                timer = true;
                StartCoroutine(InitiatePopUp(timerPopup, 2f));
                return;
            }
            if (dimensions == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true && cardValue == true && timer == true)
            {
                halted = true;
                dimensions = true;
                StartCoroutine(InitiatePopUp(dimensionsPopup, 2f));
                return;
            }
            if (otherDimensions == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true && cardValue == true && timer == true
                && dimensions == true)
            {
                halted = true;
                otherDimensions = true;
                StartCoroutine(InitiatePopUp(otherDimensionsPopup, 2f));
                return;
            }
            if (helpPause == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true && cardValue == true && timer == true
                && dimensions == true && otherDimensions == true)
            {
                halted = true;
                helpPause = true;
                StartCoroutine(InitiatePopUp(helpPausePopup, 2f));
                return;
            }
            if (stats == false && buyCard == true && moveCardSlots == true
                && buyAnotherCard == true && mergeTwoCards == true && mergeGains == true && goal == true
                && games == true && sellcard == true && cardValue == true && timer == true
                && dimensions == true && otherDimensions == true && helpPause == true)
            {
                halted = true;
                stats = true;
                StartCoroutine(InitiatePopUp(statsPopup, 2f));
                SaveGame.Save<bool>("tutorialPlayed", true);
                return;
            }
        }
    }

    public void DeactivateAllTutorialPopups()
    {
        tutorialPopups = FindObjectsByType<TutorialPopup>(FindObjectsSortMode.None);
        foreach (TutorialPopup tutorialPopup in tutorialPopups)
        {
            if (tutorialPopup.gameObject.name == "Tutorial Buy Card")
            {
                buyCardPopup = tutorialPopup.GetComponentInParent<Canvas>();
                buyCardPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Move Card Slots")
            {
                moveCardSlotsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                moveCardSlotsPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Buy Another")
            {
                buyAnotherCardPopup = tutorialPopup.GetComponentInParent<Canvas>();
                buyAnotherCardPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Merge Cards")
            {
                mergeTwoCardsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                mergeTwoCardsPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Merge Gains")
            {
                mergeGainsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                mergeGainsPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Goal")
            {
                goalPopup = tutorialPopup.GetComponentInParent<Canvas>();
                goalPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Games")
            {
                gamesPopup = tutorialPopup.GetComponentInParent<Canvas>();
                gamesPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Sell Card")
            {
                sellcardPopup = tutorialPopup.GetComponentInParent<Canvas>();
                sellcardPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Card Value")
            {
                cardValuePopup = tutorialPopup.GetComponentInParent<Canvas>();
                cardValuePopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Timer")
            {
                timerPopup = tutorialPopup.GetComponentInParent<Canvas>();
                timerPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Dimensions")
            {
                dimensionsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                dimensionsPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Other Dimensions")
            {
                otherDimensionsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                otherDimensionsPopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Help Pause")
            {
                helpPausePopup = tutorialPopup.GetComponentInParent<Canvas>();
                helpPausePopup.gameObject.SetActive(false);
            }
            else if (tutorialPopup.gameObject.name == "Tutorial Stats")
            {
                statsPopup = tutorialPopup.GetComponentInParent<Canvas>();
                statsPopup.gameObject.SetActive(false);
            }
        }

    }

    public void ContinueFromTutorialPopup()
    {
        DeactivateAllTutorialPopups();
        halted = false;
    }

    public void InitiateTutorial()
    {
        tutorialInitiated = true;
    }

    public void SkipTutorial()
    {
        levelLoader = LevelLoader.Instance;
        levelLoader.LoadSceneSelection();
        SaveGame.Save<bool>("tutorialPlayed", true);
    }

    IEnumerator InitiatePopUp(Canvas tutorialPopupCanvas, float waitTime)
    {
        yield return new WaitForSeconds(waitTime);
        tutorialPopupCanvas.gameObject.SetActive(true);
    }
}
