using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using BayatGames.SaveGameFree;

public class CardFrame : MonoBehaviour
{
    [SerializeField] float cardType;
    [SerializeField] Sprite flatSprite;
    [SerializeField] Sprite gainSprite1;
    [SerializeField] Sprite gainSprite2;
    [SerializeField] Sprite gainSprite3;
    [SerializeField] Sprite lossSprite;

    [System.NonSerialized] public bool numberActive = false;
    bool colorActive = false;
    bool shapeActive = false;
    bool wordActive = false;
    bool beatActive = false;
    bool memoryActive = false;
    bool motorActive = false;

    public NumberCard numberCard;
    public ColorCard colorCard;
    public ShapeCard shapeCard;
    public WordCard wordCard;
    public BeatCard beatCard;
    public MemoryCard memoryCard;
    public MotorCard motorCard;
    public Card cardObject;
    public bool cardSuper;
    Card cardObjectNull;
    FindClosestSlot findClosestSlot;
    ManaDisplay manaDisplay;
    CardDrawer cardDrawer;
    StatsCollectorExpanded statsCollectorExpanded;

    TutorialController tutorialController;

    NumberGain numberGainSprite;
    ColorGain colorGainSprite;
    ShapeGain shapeGainSprite;
    WordGain wordGainSprite;
    BeatGain beatGainSprite;
    MemoryGain memoryGainSprite;
    MotorGain motorGainSprite;
    SpriteRenderer numberGainSpriteRenderer;
    SpriteRenderer colorGainSpriteRenderer;
    SpriteRenderer shapeGainSpriteRenderer;
    SpriteRenderer wordGainSpriteRenderer;
    SpriteRenderer beatGainSpriteRenderer;
    SpriteRenderer memoryGainSpriteRenderer;
    SpriteRenderer motorGainSpriteRenderer;

    public SpriteRenderer backgroundSpriteRenderer;

    float numberGain = 0f;
    float colorGain = 0f;
    float shapeGain = 0f;
    float wordGain = 0f;
    float beatGain = 0f;
    float memoryGain = 0f;
    float motorGain = 0f;

    string modeNumber;
    string modeColor;
    string modeShape;
    string modeWord;
    string modeBeat;
    string modeMemory;
    string modeMotor;

    float hintWaitDuration = 3f;

    bool initialized = false;
    public bool IsInitialized => initialized;
    public int numberOfMerges = 0;
    public int maxNumberOfMerges;

    private bool recentlyPurchased = true;
    private bool isDragging;
    private bool closestComputed = true;
    private bool slotChanged = false;
    Vector2 mousePosition_;
    public SlotGeneric closestSlot;
    SlotGeneric currentSlot;
    SlotGeneric previousClosestSlot;
    //AudioSource audioCardPlaceOnSlot;
    Vector2 smallMove = new Vector2(0.000001f, 0.000001f);
    System.DateTime startTime;
    System.DateTime startTimeDrag;
    System.TimeSpan timeSpanned;
    System.TimeSpan timeSpannedDrop;
    Vector3 clickInitPosition;
    float distanceToDroppedSlot;
    float halfDistanceToDroppedSlot;

    static List<string> statsGameTypes = new List<string> {
        "Math", "Visual", "Spatial", "Verbal", "Music", "Memory", "Motor",
        "addM", "multiply", "gcd", "vector", "interval", "trigon", "sort" ,
        "addV", "subtract", "gray", "text",
        "triangle", "rectangle", "triple", "kanizsa", "sphere", "hanoi",
        "verbs", "adjectives", "nouns", "synVerbs", "synAdjectives", "grammar", "questions", "scrabble",
        "double", "single", "double fast", "single fast", "tiktok", "five",
        "every action", "show all", "show one",
        "speed accuracy", "speed accuracy halfway", "visit all slots"};
    Dictionary<string, float> dataDictCard = new Dictionary<string, float>();

    private void Start()
    {
        //cardType = PlayerPrefs.GetFloat("CardType");
        backgroundSpriteRenderer = GetComponentInChildren<CardFrameBackground>().GetComponent<SpriteRenderer>();
        //audioCardPlaceOnSlot = GetComponentInChildren<AudioSource>();
        manaDisplay = ManaDisplay.Instance;
        maxNumberOfMerges = manaDisplay.maxNumberOfMerges;
        cardDrawer = CardDrawer.Instance;
        cardSuper = cardDrawer.GetSuperCard();
        numberCard = GetNumberCard();
        colorCard = GetColorCard();
        shapeCard = GetShapeCard();
        wordCard = GetWordCard();
        beatCard = GetBeatCard();
        memoryCard = GetMemoryCard();
        motorCard = GetMotorCard();
        findClosestSlot = GetComponent<FindClosestSlot>();
        closestSlot = findClosestSlot.GetClosestSlot();
        closestSlot.SetCardObject(cardObject);
        closestSlot.SetFilledInfo(true);
        closestSlot.UpdateManaValue();
        previousClosestSlot = closestSlot;

        numberGainSprite = GetComponentInChildren<NumberGain>();
        numberGainSpriteRenderer = numberGainSprite.GetComponent<SpriteRenderer>();
        numberGainSpriteRenderer.enabled = false;
        colorGainSprite = GetComponentInChildren<ColorGain>();
        colorGainSpriteRenderer = colorGainSprite.GetComponent<SpriteRenderer>();
        colorGainSpriteRenderer.enabled = false;
        shapeGainSprite = GetComponentInChildren<ShapeGain>();
        shapeGainSpriteRenderer = shapeGainSprite.GetComponent<SpriteRenderer>();
        shapeGainSpriteRenderer.enabled = false;
        wordGainSprite = GetComponentInChildren<WordGain>();
        wordGainSpriteRenderer = wordGainSprite.GetComponent<SpriteRenderer>();
        wordGainSpriteRenderer.enabled = false;
        beatGainSprite = GetComponentInChildren<BeatGain>();
        beatGainSpriteRenderer = beatGainSprite.GetComponent<SpriteRenderer>();
        beatGainSpriteRenderer.enabled = false;
        memoryGainSprite = GetComponentInChildren<MemoryGain>();
        memoryGainSpriteRenderer = memoryGainSprite.GetComponent<SpriteRenderer>();
        memoryGainSpriteRenderer.enabled = false;
        motorGainSprite = GetComponentInChildren<MotorGain>();
        motorGainSpriteRenderer = motorGainSprite.GetComponent<SpriteRenderer>();
        motorGainSpriteRenderer.enabled = false;

        statsCollectorExpanded = StatsCollectorExpanded.Instance;
        tutorialController = TutorialController.Instance;
    }


    private void ResetDataDict()
    {
        foreach (string gameType in statsGameTypes)
        {
            if(dataDictCard.ContainsKey(gameType))
            {
                dataDictCard[gameType] = -1000f;
            }
            else
            {
                dataDictCard.Add(gameType, -1000f);
            }
        }
    }

    private void UpdateDataDict()
    {
        ResetDataDict(); //Flush the dict

        if (numberActive == true)
        {
            if(modeNumber == "add")
            {
                dataDictCard["addM"] = numberGain;
            }
            else
            {
                dataDictCard[modeNumber] = numberGain;
            }
            dataDictCard["Math"] = numberGain;
        }
        if (colorActive == true)
        {
            if (modeColor == "add")
            {
                dataDictCard["addV"] = colorGain;
            }
            else
            {
                dataDictCard[modeColor] = colorGain;
            }
            dataDictCard["Visual"] = colorGain;
        }
        if (shapeActive == true)
        {
            dataDictCard[modeShape] = shapeGain;
            dataDictCard["Spatial"] = shapeGain;
        }
        if (wordActive == true)
        {
            dataDictCard[modeWord] = wordGain;
            dataDictCard["Verbal"] = wordGain;
        }
        if (beatActive == true)
        {
            dataDictCard[modeBeat] = beatGain;
            dataDictCard["Music"] = beatGain;
        }
        if (memoryActive == true)
        {
            dataDictCard[modeMemory] = memoryGain;
            dataDictCard["Memory"] = memoryGain;
        }
        if (motorActive == true)
        {
            dataDictCard[modeMotor] = motorGain;
            dataDictCard["Motor"] = motorGain;
        }

    }

    private void PerformMotorAction()
    {
        if(motorActive)
        {
            timeSpannedDrop = System.DateTime.UtcNow - startTimeDrag;
            Vector3 vectorDeltaDrop = Camera.main.ScreenToWorldPoint(Input.mousePosition) - clickInitPosition;
            distanceToDroppedSlot = (closestSlot.transform.position - transform.position).sqrMagnitude;

            motorGain = this.motorCard.MergeMotorCard((float)timeSpannedDrop.TotalSeconds, vectorDeltaDrop.sqrMagnitude,
                distanceToDroppedSlot, findClosestSlot.minDistanceAnchor, findClosestSlot.minDistanceSlots);

            findClosestSlot.ReInitMinDistances();

            if (motorGain == -1f)
            {
                motorGainSpriteRenderer.sprite = lossSprite;
            }
            else if (motorGain == 0f)
            {
                motorGainSpriteRenderer.sprite = flatSprite;
            }
            else if (motorGain == 1f)
            {
                motorGainSpriteRenderer.sprite = gainSprite1;
            }
            else if (motorGain == 2f)
            {
                motorGainSpriteRenderer.sprite = gainSprite2;
            }
            else if (motorGain == 3f)
            {
                motorGainSpriteRenderer.sprite = gainSprite3;
            }

            UpdateDataDict();
            statsCollectorExpanded.UpdateGameStats(dataDictCard, false);

            StartCoroutine(ShowMotorGainIcon());

        }
    }

   

    private void PerformBeatAction(string emptyOrMerge="empty", int slotNumber=1)
    {
        if (beatActive)
        {
            if(modeBeat == "double" || modeBeat == "single" || modeBeat == "double fast" || modeBeat == "single fast")
            {
                beatGain = this.beatCard.MergeBeatCard();
            }
            else if(modeBeat == "tiktok")
            {
                if(emptyOrMerge == "empty")
                {
                    beatGain = this.beatCard.MergeBeatCard();
                }
                else if(emptyOrMerge == "merge")
                {
                    beatGain = this.beatCard.MergeBeatCard(2);
                }
            }
            else if (modeBeat == "five")
            {
                beatGain = this.beatCard.MergeBeatCard(slotNumber);
            }

            
            if (beatGain == -1f)
            {
                beatGainSpriteRenderer.sprite = lossSprite;
            }
            else if (beatGain == 0f)
            {
                beatGainSpriteRenderer.sprite = flatSprite;
            }
            else if (beatGain == 1f)
            {
                beatGainSpriteRenderer.sprite = gainSprite1;
                //beatGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
            }
            else if (beatGain == 2f)
            {
                beatGainSpriteRenderer.sprite = gainSprite2;
                //beatGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
            }
            else if (beatGain == 3f)
            {
                beatGainSpriteRenderer.sprite = gainSprite3;
                //beatGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
            }

            UpdateDataDict();
            statsCollectorExpanded.UpdateGameStats(dataDictCard, false);

            StartCoroutine(ShowBeatGainIcon());

        }
    }

    /// <summary>
    /// Idempotently run ActivateComponents() if it hasn't run yet.
    /// Safe to call from any path that needs the card's dimensions to be
    /// resolved (move, sell, agent serialization, ...). Without this, code
    /// that reads <c>numberCard.numberSelected</c> in the same frame as the
    /// draw will see the <c>-1000f</c> sentinel and treat the card as blank.
    /// Bails out if Start() hasn't run yet (numberCard etc. unresolved).
    /// </summary>
    public void EnsureActivated()
    {
        if (initialized) return;
        // ActivateComponents() needs all the card dimension components.
        // CardFrame.Start() populates them; if it hasn't run yet, skip and
        // let Update() handle it on the next frame.
        if (numberCard == null || colorCard == null || shapeCard == null ||
            wordCard == null || beatCard == null || memoryCard == null ||
            motorCard == null) return;
        ActivateComponents();
        initialized = true;
    }

    private void Update()
    {
        if (initialized)
        {
            if (isDragging == true)
            {
                mousePosition_ = Camera.main.ScreenToWorldPoint(Input.mousePosition) - transform.position;
                transform.Translate(mousePosition_);
                // Change the color of the closest clot
                if (mousePosition_.sqrMagnitude < smallMove.sqrMagnitude)
                {
                    closestSlot = findClosestSlot.GetClosestSlot();
                    //if (closestSlot == currentSlot)
                    //{
                    //    return;
                    //}

                    if (closestSlot != previousClosestSlot)
                    {
                        slotChanged = true;
                        startTime = System.DateTime.UtcNow;
                        previousClosestSlot = closestSlot;
                    }
                    else
                    {
                        slotChanged = false;
                    }
                    SlotNew slotNewTest = closestSlot.GetComponent<SlotNew>();
                    SlotSell slotSellTest = closestSlot.GetComponent<SlotSell>();
                    if (closestSlot != currentSlot && slotNewTest == null && slotSellTest == null)
                    {
                        closestSlot.GetComponent<SpriteRenderer>().color = Color.black;
                        SlotGeneric[] slotGenericList = FindObjectsByType<SlotGeneric>(FindObjectsSortMode.None);
                        foreach (SlotGeneric slotGeneric in slotGenericList)
                        {
                            if (slotGeneric != closestSlot)
                            {
                                slotGeneric.GetComponent<SpriteRenderer>().color = Color.white;
                            }

                        }

                        if (closestSlot.GetFilledInfo() == true)
                        {
                            timeSpanned = System.DateTime.UtcNow - startTime;
                            if (timeSpanned.TotalSeconds > hintWaitDuration)
                            {
                                (numberGain, colorGain, shapeGain, wordGain, memoryGain) = AnimateGain(false);

                            }
                        }

                        return;
                    }
                }
            }
            else if (isDragging == false && closestComputed == false)
            {
                closestComputed = true;
                closestSlot = findClosestSlot.GetClosestSlot();

                // Compute the bridge action ID for this drop BEFORE any branch
                // mutates currentSlot. -1 means "not a real action" (snap-back
                // branches don't emit a human_step). The three real-action
                // branches below set this via the helper before they return.
                int humanActionId = -1;
                if (AgentBridge.recordingMode && currentSlot != null && closestSlot != null
                    && closestSlot != currentSlot)
                {
                    int srcIdx = (currentSlot.GetComponent<SlotNew>() != null)
                        ? 0 : currentSlot.slotNumber;
                    if (closestSlot.GetComponent<SlotSell>() != null)
                        humanActionId = 31 + srcIdx;                                 // SELL(src)
                    else if (closestSlot.GetComponent<SlotNew>() == null)
                        humanActionId = 1 + srcIdx * 5 + (closestSlot.slotNumber - 1); // MOVE/MERGE
                }

                //Trying to drop onto itself
                if (closestSlot == currentSlot)
                {
                    transform.position = currentSlot.transform.position;
                    currentSlot.SetCardObject(cardObject);
                    currentSlot.UpdateManaValue();
                    currentSlot.SetFilledInfo(true);
                    return;
                }

                SlotNew slotNewTest = closestSlot.GetComponent<SlotNew>();
                SlotSell slotSellTest = closestSlot.GetComponent<SlotSell>();

                //Dragged onto Slot New, is illegal to do.
                if (slotNewTest != null)
                {
                    transform.position = currentSlot.transform.position;
                    currentSlot.SetCardObject(cardObject);
                    currentSlot.UpdateManaValue();
                    currentSlot.SetFilledInfo(true);
                    return;
                }
                //Dragged onto Slot Sell, sell and destroy.
                else if (slotSellTest != null)
                {
                    //PerformMotorAction();
                    //PerformBeatAction("empty", closestSlot.slotNumber);
                    transform.position = closestSlot.transform.position;
                    closestSlot.SetCardObject(cardObject);
                    closestSlot.UpdateManaValue();
                    closestSlot.SetCardObject(cardObjectNull);
                    closestSlot.SetFilledInfo(false);
                    currentSlot.SetFilledInfo(false);
                    currentSlot.SetCardObject(cardObjectNull);
                    currentSlot.UpdateManaValue();
                    slotSellTest.SellEffectInitiate();

                    Destroy(cardObject.gameObject, 0.3f);
                    Destroy(this.gameObject, 0.1f);

                    if (tutorialController && tutorialController.tutorialInitiated)
                    {
                        tutorialController.sellcard = true;
                        tutorialController.ContinueFromTutorialPopup();
                    }
                    if (humanActionId >= 0 && AgentBridge.Instance != null)
                        AgentBridge.Instance.EmitHumanStep(humanActionId);
                    return;
                }
                //Dragged onto an empty slot, move and clean the previous.
                if (closestSlot.GetFilledInfo() == false)
                {
                    if(recentlyPurchased)
                    {
                        PerformMotorAction();
                        PerformBeatAction("empty", closestSlot.slotNumber);
                    }
                    recentlyPurchased = false;
                    transform.position = closestSlot.transform.position;
                    currentSlot.SetFilledInfo(false);
                    currentSlot.SetCardObject(cardObjectNull);
                    currentSlot.UpdateManaValue();
                    closestSlot.SetFilledInfo(true);
                    closestSlot.SetCardObject(cardObject);
                    closestSlot.UpdateManaValue();
                    closestSlot.GetComponent<SpriteRenderer>().color = Color.white;
                    currentSlot.GetComponent<SpriteRenderer>().color = Color.white;
                    currentSlot = closestSlot;
                    //audioCardPlaceOnSlot.Play();
                    if (tutorialController && tutorialController.tutorialInitiated)
                    {
                        tutorialController.moveCardSlots = true;
                        tutorialController.ContinueFromTutorialPopup();
                    }
                    if(modeMemory == "every action") //show all cards for every action of the cards
                    {
                        this.memoryCard.ShowAllCardInfo();
                    }
                    else if (modeMemory == "show one" || modeMemory == "show all") //show all cards for every action of the cards
                    {
                        this.memoryCard.ShowCardInfo();
                    }
                    if (humanActionId >= 0 && AgentBridge.Instance != null)
                        AgentBridge.Instance.EmitHumanStep(humanActionId);
                    return;
                }

                //Initiate card merge.
                else
                {
                    if (numberOfMerges < maxNumberOfMerges)
                    {
                        recentlyPurchased = false;
                        PerformMotorAction();
                        PerformBeatAction("merge", closestSlot.slotNumber);
                        numberOfMerges++;
                        transform.position = closestSlot.transform.position;
                        closestSlot.GetComponent<SpriteRenderer>().color = Color.white;
                        currentSlot.GetComponent<SpriteRenderer>().color = Color.white;
                        Card cardOther = closestSlot.GetCardObject();
                        if (cardOther == null)
                        {
                            Debug.Log("Tried to merge with null card in slot 1.");
                            return;
                        }
                        CardFrame cardFrameOther = cardOther.GetCardFrame();
                        if (cardFrameOther == null)
                        {
                            Debug.Log("Tried to merge with null card in slot 2.");
                            return;
                        }
                        NumberCard numberCardOther = cardFrameOther.numberCard;
                        ColorCard colorCardOther = cardFrameOther.colorCard;
                        ShapeCard shapeCardOther = cardFrameOther.shapeCard;
                        WordCard wordCardOther = cardFrameOther.wordCard;
                        if (numberCardOther == null)
                        {
                            Debug.Log("Tried to merge with null card in slot 3.");
                            return;
                        }

                        (numberGain, colorGain, shapeGain, wordGain, memoryGain) = AnimateGain(true);
                        UpdateDataDict();
                        statsCollectorExpanded.UpdateGameStats(dataDictCard, true);

                        this.numberCard.MergeNumberCard(numberCardOther.numberSelected);
                        this.colorCard.MergeColorCard(colorCardOther.colorSelected, colorCardOther.colorIndexGray);
                        this.shapeCard.MergeShapeCard(shapeCardOther.spriteSelectedIndex);
                        this.wordCard.MergeWordCard(wordCardOther.wordSelectedList);
                        this.memoryCard.MergeMemoryCard(memoryGain);

                        closestSlot.SetFilledInfo(true);
                        closestSlot.SetCardObject(cardObject);
                        closestSlot.UpdateManaValue();

                        currentSlot.SetFilledInfo(false);
                        currentSlot.SetCardObject(cardObjectNull);
                        currentSlot.UpdateManaValue();

                        Destroy(cardOther.gameObject, 0.1f);
                        Destroy(cardFrameOther.gameObject, 0.1f);
                        
                        currentSlot = closestSlot;
                        //currentSlot.MergeEffectInitiate();

                        if (tutorialController && tutorialController.tutorialInitiated)
                        {
                            tutorialController.mergeTwoCards = true;
                            tutorialController.ContinueFromTutorialPopup();
                        }

                        if (humanActionId >= 0 && AgentBridge.Instance != null)
                            AgentBridge.Instance.EmitHumanStep(humanActionId);
                        return;
                    }
                    else
                    {
                        // TODO: automatically delete the card, since no option but to sell
                        // Needs an animation and an emphasis on the final mana value
                        transform.position = currentSlot.transform.position;
                        currentSlot.SetCardObject(cardObject);
                        currentSlot.UpdateManaValue();
                        currentSlot.SetFilledInfo(true);
                        Debug.Log("Max number of merges reached.");
                        return;
                    }

                }

            }
        }
        else
        {
            ActivateComponents();
            //ResetDataDict();
            initialized = true;
        }

    }

    private (float numberGain, float colorGain, float shapeGain, float wordGain, float memoryGain)
        AnimateGain(bool duringMerge = false)
    {
        startTime = System.DateTime.UtcNow;
        Card cardOther = closestSlot.GetCardObject();
        if (cardOther != null)
        {
            CardFrame cardFrameOther = cardOther.GetCardFrame();
            if (cardFrameOther != null)
            {
                NumberCard numberCardOther = cardFrameOther.numberCard;
                ColorCard colorCardOther = cardFrameOther.colorCard;
                ShapeCard shapeCardOther = cardFrameOther.shapeCard;
                WordCard wordCardOther = cardFrameOther.wordCard;
                numberGain = this.numberCard.ComputeMergeNumberGain(numberCardOther.numberSelected);
                colorGain = this.colorCard.ComputeMergeColorGain(colorCardOther.colorSelected, colorCardOther.colorIndexGray);
                shapeGain = this.shapeCard.ComputeMergeShapeGain(shapeCardOther.spriteSelectedIndex);
                wordGain = this.wordCard.ComputeMergeWordGain(wordCardOther.wordSelectedList);
                ComputeMemoryGain();

                if (numberGain == -1f)
                {
                    numberGainSpriteRenderer.sprite = lossSprite;
                }
                else if (numberGain == 0f)
                {
                    numberGainSpriteRenderer.sprite = flatSprite;
                }
                else if (numberGain == 1f)
                {
                    numberGainSpriteRenderer.sprite = gainSprite1;
                    //numberGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
                }
                else if (numberGain == 2f)
                {
                    numberGainSpriteRenderer.sprite = gainSprite2;
                    //numberGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
                }
                else if (numberGain == 3f)
                {
                    numberGainSpriteRenderer.sprite = gainSprite3;
                    //numberGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
                }


                if (colorGain == -1f)
                {
                    colorGainSpriteRenderer.sprite = lossSprite;
                }
                else if (colorGain == 0f)
                {
                    colorGainSpriteRenderer.sprite = flatSprite;
                }
                else if (colorGain == 1f)
                {
                    colorGainSpriteRenderer.sprite = gainSprite1;
                    //colorGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
                }
                else if (colorGain == 2f)
                {
                    colorGainSpriteRenderer.sprite = gainSprite2;
                    //colorGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
                }
                else if (colorGain == 3f)
                {
                    colorGainSpriteRenderer.sprite = gainSprite3;
                    //colorGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
                }


                if (shapeGain == -1f)
                {
                    shapeGainSpriteRenderer.sprite = lossSprite;
                }
                else if (shapeGain == 0f)
                {
                    shapeGainSpriteRenderer.sprite = flatSprite;
                }
                else if (shapeGain == 1f)
                {
                    shapeGainSpriteRenderer.sprite = gainSprite1;
                    //shapeGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
                }
                else if (shapeGain == 2f)
                {
                    shapeGainSpriteRenderer.sprite = gainSprite2;
                    //shapeGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
                }
                else if (shapeGain == 3f)
                {
                    shapeGainSpriteRenderer.sprite = gainSprite3;
                    //shapeGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
                }


                if (wordGain == -1f)
                {
                    wordGainSpriteRenderer.sprite = lossSprite;
                }
                else if (wordGain == 0f)
                {
                    wordGainSpriteRenderer.sprite = flatSprite;
                }
                else if (wordGain == 1f)
                {
                    wordGainSpriteRenderer.sprite = gainSprite1;
                    //wordGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
                }
                else if (wordGain == 2f)
                {
                    wordGainSpriteRenderer.sprite = gainSprite2;
                    //wordGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
                }
                else if (wordGain == 3f)
                {
                    wordGainSpriteRenderer.sprite = gainSprite3;
                    //wordGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
                }


                if (memoryGain == -1f)
                {
                    memoryGainSpriteRenderer.sprite = lossSprite;
                }
                else if (memoryGain == 0f)
                {
                    memoryGainSpriteRenderer.sprite = flatSprite;
                }
                else if (memoryGain == 1f)
                {
                    memoryGainSpriteRenderer.sprite = gainSprite1;
                    //beatGainSpriteRenderer.size = new Vector2(0.5f, 0.5f);
                }
                else if (memoryGain == 2f)
                {
                    memoryGainSpriteRenderer.sprite = gainSprite2;
                    //beatGainSpriteRenderer.size = new Vector2(0.6f, 0.6f);
                }
                else if (memoryGain == 3f)
                {
                    memoryGainSpriteRenderer.sprite = gainSprite3;
                    //beatGainSpriteRenderer.size = new Vector2(0.7f, 0.7f);
                }

                StartCoroutine(ShowGainIcons(duringMerge));
            }
        }

        return (numberGain, colorGain, shapeGain, wordGain, memoryGain);
    }


    IEnumerator ShowMotorGainIcon()
    {
        if (motorActive)
        {
            motorGainSpriteRenderer.enabled = true;
        }
        yield return new WaitForSeconds(2);
        motorGainSpriteRenderer.enabled = false;
    }

    IEnumerator ShowBeatGainIcon()
    {
        if (beatActive)
        {
            beatGainSpriteRenderer.enabled = true;
        }
        yield return new WaitForSeconds(2);
        beatGainSpriteRenderer.enabled = false;
    }


    IEnumerator ShowGainIcons(bool duringMerge)
    {
        if (numberActive)
        {
            numberGainSpriteRenderer.enabled = true;
        }
        if (colorActive)
        {
            colorGainSpriteRenderer.enabled = true;
        }
        if (shapeActive)
        {
            shapeGainSpriteRenderer.enabled = true;
        }
        if (wordActive)
        {
            wordGainSpriteRenderer.enabled = true;
        }
        
        yield return new WaitForSeconds(2);
        numberGainSpriteRenderer.enabled = false;
        colorGainSpriteRenderer.enabled = false;
        shapeGainSpriteRenderer.enabled = false;
        wordGainSpriteRenderer.enabled = false;
        memoryGainSpriteRenderer.enabled = false;
    }


    private void ActivateComponents()
    {
        if (cardType == 1)
        {
            float randomNumber1 = Random.Range(0f, 1f);
            if (randomNumber1 < 0.25)
            {
                numberCard.SetActivated(true);
                modeNumber = "add";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (randomNumber1 >= 0.25 && randomNumber1 < 0.5)
            {
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                colorActive = true;
            }
            else if (randomNumber1 >= 0.5 && randomNumber1 < 0.75)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                shapeActive = true;
            }
            else
            {
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                wordActive = true;
            }
        }

        else if (cardType == 2)
        {
            float randomNumber1 = Random.Range(0f, 6f);
            if (randomNumber1 < 1)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                numberActive = true;
                colorActive = true;
            }
            else if (randomNumber1 >= 1 && randomNumber1 < 2)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                numberActive = true;
                shapeActive = true;
            }
            else if (randomNumber1 >= 2 && randomNumber1 < 3)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                numberActive = true;
                wordActive = true;
            }
            else if (randomNumber1 >= 3 && randomNumber1 < 4)
            {
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                colorActive = true;
                shapeActive = true;

            }
            else if (randomNumber1 >= 4 && randomNumber1 < 5)
            {
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                colorActive = true;
                wordActive = true;
            }
            else
            {
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                shapeActive = true;
                wordActive = true;
            }
        }

        else if (cardType == 3)
        {
            float randomNumber1 = Random.Range(0f, 1f);
            if (randomNumber1 < 0.25)
            {
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                colorActive = true;
                shapeActive = true;
                wordActive = true;
            }
            else if (randomNumber1 >= 0.25 && randomNumber1 < 0.5)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                numberActive = true;
                shapeActive = true;
                wordActive = true;
            }
            else if (randomNumber1 >= 0.5 && randomNumber1 < 0.75)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                numberActive = true;
                colorActive = true;
                wordActive = true;
            }
            else
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                numberActive = true;
                colorActive = true;
                shapeActive = true;
            }
        }

        else if (cardType == 4)
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            colorCard.SetActivated(true);
            colorCard.SetColor();
            modeColor = "add";
            shapeCard.SetActivated(true);
            shapeCard.SetShape();
            modeShape = "triangle";
            wordCard.SetActivated(true);
            wordCard.SetWord();
            modeWord = "verbs";
            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
        }

        else if (cardType == 5) //only number card, add
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            numberActive = true;
        }

        else if (cardType == 6) //only color card, add
        {
            colorCard.SetActivated(true);
            colorCard.SetColor();
            modeColor = "add";
            colorActive = true;
        }

        else if (cardType == 7) //only shape card, triangle
        {
            shapeCard.SetActivated(true);
            shapeCard.SetShape();
            modeShape = "triangle";
            shapeActive = true;
        }

        else if (cardType == 8) //only word card, verbs
        {
            wordCard.SetActivated(true);
            wordCard.SetWord();
            modeWord = "verbs";
            wordActive = true;
        }

        else if (cardType == 9) //only number card, multiply
        {
            numberCard.SetActivated(true);
            numberCard.SetModeNumber("multiply");
            modeNumber = "multiply";
            numberCard.SetNumber();
            numberActive = true;
        }

        else if (cardType == 10) //only color card, subtract
        {
            colorCard.SetActivated(true);
            colorCard.SetModeColor("subtract");
            colorCard.SetColor();
            modeColor = "subtract";
            colorActive = true;
        }

        else if (cardType == 11) //only shape card, rectangle
        {
            shapeCard.SetActivated(true);
            shapeCard.SetModeShape("rectangle");
            modeShape = "rectangle";
            shapeCard.SetShape();
            shapeActive = true;
        }

        else if (cardType == 12) //only word card, adjective
        {
            wordCard.SetActivated(true);
            wordCard.SetModeWord("adjectives");
            wordCard.SetWord();
            modeWord = "adjectives";
            wordActive = true;
        }

        if (cardType == 13) //13, 14, 15, 16 are all of the above 4 (multiply, subtract, rectangle, adj)
        {
            float randomNumber1 = Random.Range(0f, 1f);
            if (randomNumber1 < 0.25)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (randomNumber1 >= 0.25 && randomNumber1 < 0.5)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                colorActive = true;
            }
            else if (randomNumber1 >= 0.5 && randomNumber1 < 0.75)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                shapeActive = true;
            }
            else
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                wordActive = true;
            }
        }

        else if (cardType == 14)
        {
            float randomNumber1 = Random.Range(0f, 6f);
            if (randomNumber1 < 1)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                colorCard.SetActivated(true);
                modeColor = "subtract";
                colorCard.SetModeColor("subtract");
                colorCard.SetColor();
                numberActive = true;
                colorActive = true;
            }
            else if (randomNumber1 >= 1 && randomNumber1 < 2)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                numberActive = true;
                shapeActive = true;
            }
            else if (randomNumber1 >= 2 && randomNumber1 < 3)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                numberActive = true;
                wordActive = true;

            }
            else if (randomNumber1 >= 3 && randomNumber1 < 4)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                colorActive = true;
                shapeActive = true;

            }
            else if (randomNumber1 >= 4 && randomNumber1 < 5)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                colorActive = true;
                wordActive = true;

            }
            else
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                shapeActive = true;
                wordActive = true;
            }
        }

        else if (cardType == 15)
        {
            float randomNumber1 = Random.Range(0f, 1f);
            if (randomNumber1 < 0.25)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                colorActive = true;
                shapeActive = true;
                wordActive = true;
            }
            else if (randomNumber1 >= 0.25 && randomNumber1 < 0.5)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                numberActive = true;
                shapeActive = true;
                wordActive = true;
            }
            else if (randomNumber1 >= 0.5 && randomNumber1 < 0.75)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                numberCard.SetNumber();
                modeNumber = "multiply";
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                numberActive = true;
                colorActive = true;
                wordActive = true;
            }
            else
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                modeColor = "subtract";
                colorCard.SetColor();
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                numberActive = true;
                colorActive = true;
                shapeActive = true;
            }
        }

        else if (cardType == 16)
        {
            numberCard.SetActivated(true);
            numberCard.SetModeNumber("multiply");
            modeNumber = "multiply";
            numberCard.SetNumber();
            colorCard.SetActivated(true);
            colorCard.SetModeColor("subtract");
            modeColor = "subtract";
            colorCard.SetColor();
            shapeCard.SetActivated(true);
            shapeCard.SetModeShape("rectangle");
            shapeCard.SetShape();
            modeShape = "rectangle";
            wordCard.SetActivated(true);
            wordCard.SetModeWord("adjectives");
            wordCard.SetWord();
            modeWord = "adjectives";
            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
        }
        else if (cardType == 17) //All empty card with no dimension at all, "beat only" level, double beat
        {
            numberCard.SetActivated(false);
            numberCard.SetNumber();
            colorCard.SetActivated(false);
            colorCard.SetColor();
            shapeCard.SetActivated(false);
            shapeCard.SetShape();
            wordCard.SetActivated(false);
            wordCard.SetWord();
            beatCard.SetActivated(true);
            beatCard.SetBeat();
            modeBeat = "double";
            beatActive = true;
        }
        else if (cardType == 18) //Number, add + Memory
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            numberActive = true;
            memoryCard.SetActivated(true);
            memoryCard.SetMemory();
            memoryActive = true;
            modeMemory = "every action";
        }
        else if (cardType == 19) //All empty card with no dimension at all, "motor only" level
        {
            numberCard.SetActivated(false);
            numberCard.SetNumber();
            colorCard.SetActivated(false);
            colorCard.SetColor();
            shapeCard.SetActivated(false);
            shapeCard.SetShape();
            wordCard.SetActivated(false);
            wordCard.SetWord();
            motorCard.SetActivated(true);
            motorCard.SetMotor();
            modeMotor = "speed accuracy";
            motorActive = true;
        }
        else if (cardType == 20) //Number add + Beat single beat
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            colorCard.SetActivated(false);
            colorCard.SetColor();
            shapeCard.SetActivated(false);
            shapeCard.SetShape();
            wordCard.SetActivated(false);
            wordCard.SetWord();
            beatCard.SetActivated(true);
            beatCard.SetModeBeat("single");
            beatCard.SetBeat();
            modeBeat = "single";
            numberActive = true;
            beatActive = true;
        }

        else if (cardType == 21) //Number add +  color add + Shape triangle + Word verbs + Memory
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            colorCard.SetActivated(true);
            colorCard.SetColor();
            modeColor = "add";
            shapeCard.SetActivated(true);
            shapeCard.SetShape();
            modeShape = "triangle";
            wordCard.SetActivated(true);
            wordCard.SetWord();
            modeWord = "verbs";
            memoryCard.SetActivated(true);
            memoryCard.SetMemory();
            modeMemory = "every action";

            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
            memoryActive = true;
            
        }

        else if (cardType == 22) //Number add +  color add + Shape triangle + Word verbs + Motor
        {
            numberCard.SetActivated(true);
            numberCard.SetNumber();
            modeNumber = "add";
            colorCard.SetActivated(true);
            colorCard.SetColor();
            modeColor = "add";
            shapeCard.SetActivated(true);
            shapeCard.SetShape();
            modeShape = "triangle";
            wordCard.SetActivated(true);
            wordCard.SetWord();
            modeWord = "verbs";
            motorCard.SetActivated(true);
            motorCard.SetMotor();
            modeMotor = "speed accuracy";

            numberActive = true;
            colorActive = true;
            shapeActive = true;
            wordActive = true;
            motorActive = true;
        }

        else if (cardType > 1000f) // Any combination card type encoding
        {
            float numberSelection = Mathf.Floor(cardType / 1000000f);
            cardType = cardType - numberSelection * 1000000f;
            float colorSelection = Mathf.Floor(cardType / 100000f);
            cardType = cardType - colorSelection * 100000f;
            float shapeSelection = Mathf.Floor(cardType / 10000f);
            cardType = cardType - shapeSelection * 10000f;
            float wordSelection = Mathf.Floor(cardType / 1000f);
            cardType = cardType - wordSelection * 1000f;
            float beatSelection = Mathf.Floor(cardType / 100f);
            cardType = cardType - beatSelection * 100f;
            float memorySelection = Mathf.Floor(cardType / 10f);
            cardType = cardType - memorySelection * 10f;
            float motorSelection = cardType;

            if(numberSelection == 2f)
            {
                numberCard.SetActivated(true);
                numberCard.SetNumber();
                modeNumber = "add";
                numberActive = true;
            }
            else if(numberSelection == 3f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("multiply");
                modeNumber = "multiply";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (numberSelection == 4f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("gcd");
                modeNumber = "gcd";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (numberSelection == 5f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("vector");
                modeNumber = "vector";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (numberSelection == 6f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("interval");
                modeNumber = "interval";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (numberSelection == 7f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("trigon");
                modeNumber = "trigon";
                numberCard.SetNumber();
                numberActive = true;
            }
            else if (numberSelection == 8f)
            {
                numberCard.SetActivated(true);
                numberCard.SetModeNumber("sort");
                modeNumber = "sort";
                numberCard.SetNumber();
                numberActive = true;
            }

            if (colorSelection == 2f)
            {
                colorCard.SetActivated(true);
                colorCard.SetColor();
                modeColor = "add";
                colorActive = true;
            }
            else if (colorSelection == 3f)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("subtract");
                colorCard.SetColor();
                modeColor = "subtract";
                colorActive = true;
            }
            else if (colorSelection == 4f)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("gray");
                colorCard.SetColor();
                modeColor = "gray";
                colorActive = true;
            }
            else if (colorSelection == 5f)
            {
                colorCard.SetActivated(true);
                colorCard.SetModeColor("text");
                colorCard.SetColor();
                modeColor = "text";
                colorActive = true;
            }

            if (shapeSelection == 2f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetShape();
                modeShape = "triangle";
                shapeActive = true;
            }
            else if (shapeSelection == 3f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("rectangle");
                shapeCard.SetShape();
                modeShape = "rectangle";
                shapeActive = true;
            }
            else if (shapeSelection == 4f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("triple");
                shapeCard.SetShape();
                modeShape = "triple";
                shapeActive = true;
            }
            else if (shapeSelection == 5f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("kanizsa");
                shapeCard.SetShape();
                modeShape = "kanizsa";
                shapeActive = true;
            }
            else if (shapeSelection == 6f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("sphere");
                shapeCard.SetShape();
                modeShape = "sphere";
                shapeActive = true;
            }
            else if (shapeSelection == 7f)
            {
                shapeCard.SetActivated(true);
                shapeCard.SetModeShape("hanoi");
                shapeCard.SetShape();
                modeShape = "hanoi";
                shapeActive = true;
            }

            if (wordSelection == 2f)
            {
                wordCard.SetActivated(true);
                wordCard.SetWord();
                modeWord = "verbs";
                wordActive = true;
            }
            else if (wordSelection == 3f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("adjectives");
                wordCard.SetWord();
                modeWord = "adjectives";
                wordActive = true;
            }
            //else if (wordSelection == 4f)
            //{
            //    wordCard.SetActivated(true);
            //    wordCard.SetModeWord("prepositions");
            //    wordCard.SetWord();
            //    modeWord = "prepositions";
            //    wordActive = true;
            //}
            else if (wordSelection == 4f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("nouns");
                wordCard.SetWord();
                modeWord = "nouns";
                wordActive = true;
            }
            else if (wordSelection == 5f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("synVerbs");
                wordCard.SetWord();
                modeWord = "synVerbs";
                wordActive = true;
            }
            else if (wordSelection == 6f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("synAdjectives");
                wordCard.SetWord();
                modeWord = "synAdjectives";
                wordActive = true;
            }
            else if (wordSelection == 7f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("grammar");
                wordCard.SetWord();
                modeWord = "grammar";
                wordActive = true;
            }
            else if (wordSelection == 8f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("questions");
                wordCard.SetWord();
                modeWord = "questions";
                wordActive = true;
            }
            else if (wordSelection == 9f)
            {
                wordCard.SetActivated(true);
                wordCard.SetModeWord("scrabble");
                wordCard.SetWord();
                modeWord = "scrabble";
                wordActive = true;
            }

            if (beatSelection == 2f)
            {
                beatCard.SetActivated(true);
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "double";
            }
            else if(beatSelection == 3f)
            {
                beatCard.SetActivated(true);
                beatCard.SetModeBeat("single");
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "single";
            }
            else if (beatSelection == 4f)
            {
                beatCard.SetActivated(true);
                beatCard.SetModeBeat("double fast");
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "double fast";
            }
            else if (beatSelection == 5f)
            {
                beatCard.SetActivated(true);
                beatCard.SetModeBeat("single fast");
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "single fast";
            }
            else if (beatSelection == 6f)
            {
                beatCard.SetActivated(true);
                beatCard.SetModeBeat("tiktok");
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "tiktok";
            }
            else if (beatSelection == 7f)
            {
                beatCard.SetActivated(true);
                beatCard.SetModeBeat("five");
                beatCard.SetBeat();
                beatActive = true;
                modeBeat = "five";
            }

            if (memorySelection == 2f)
            {
                memoryCard.SetActivated(true);
                memoryCard.SetMemory();
                memoryActive = true;
                modeMemory = "every action";
            }
            else if (memorySelection ==3f)
            {
                memoryCard.SetActivated(true);
                memoryCard.SetModeMemory("show all");
                memoryCard.SetMemory();
                memoryActive = true;
                modeMemory = "show all";
            }
            else if (memorySelection == 4f)
            {
                memoryCard.SetActivated(true);
                memoryCard.SetModeMemory("show one");
                memoryCard.SetMemory();
                memoryActive = true;
                modeMemory = "show one";
            }

            if (motorSelection == 2f)
            {
                motorCard.SetActivated(true);
                motorCard.SetMotor();
                modeMotor = "speed accuracy";
                motorActive = true;
            }
            else if(motorSelection == 3f)
            {
                motorCard.SetActivated(true);
                motorCard.SetModeMotor("speed accuracy halfway"); 
                motorCard.SetMotor();
                modeMotor = "speed accuracy halfway";
                motorActive = true;
            }
            else if (motorSelection == 4f)
            {
                motorCard.SetActivated(true);
                motorCard.SetModeMotor("visit all slots"); 
                motorCard.SetMotor();
                modeMotor = "visit all slots";
                motorActive = true;
            }


            //Debug.Log(numberSelection.ToString() + "   " + colorSelection.ToString() + "   " +
            //    shapeSelection.ToString() + "   " + wordSelection.ToString() + "   " +
            //    beatSelection.ToString() + "   " + memorySelection.ToString() + "   " +
            //    motorSelection.ToString() + "   ");

        }

    }

    public NumberCard GetNumberCard()
    {
        return GetComponentInChildren<NumberCard>();
    }

    public ColorCard GetColorCard()
    {
        return GetComponentInChildren<ColorCard>();
    }

    public ShapeCard GetShapeCard()
    {
        return GetComponentInChildren<ShapeCard>();
    }

    public WordCard GetWordCard()
    {
        return GetComponentInChildren<WordCard>();
    }

    public BeatCard GetBeatCard()
    {
        return GetComponentInChildren<BeatCard>();
    }

    public MemoryCard GetMemoryCard()
    {
        return GetComponentInChildren<MemoryCard>();
    }

    public MotorCard GetMotorCard()
    {
        return GetComponentInChildren<MotorCard>();
    }

    private void ComputeMemoryGain()
    {
        if(memoryActive)
        {
            float numberOfActiveFields = 0f;
            memoryGain = 0f;
            if (numberActive)
            {
                memoryGain += numberGain;
                numberOfActiveFields++;
            }
            if (colorActive)
            {
                memoryGain += colorGain;
                numberOfActiveFields++;
            }
            if (shapeActive)
            {
                memoryGain += shapeGain;
                numberOfActiveFields++;
            }
            if (wordActive)
            {
                memoryGain += wordGain;
                numberOfActiveFields++;
            }
            memoryGain = Mathf.Round(memoryGain / (numberOfActiveFields + 0.001f));
        }
    }

    //void OnMouseOver()
    //{
    //    if (Input.GetMouseButtonDown(0))
    //    {
    //        isDragging = true;
    //        closestComputed = false;
    //        currentSlot = findClosestSlot.GetClosestSlot();
    //        startTime = System.DateTime.UtcNow;
    //        startTimeDrag = System.DateTime.UtcNow;
    //        clickInitPosition = Camera.main.ScreenToWorldPoint(Input.mousePosition);
    //        Debug.Log("Mouse is down");
    //    }
    //}


    // ------------------------------------------------------------------
    // Programmatic drop — called by AgentBridge for AI-controlled play.
    // Replicates the logic in Update() when isDragging becomes false.
    // Motor params are injected from the Python-side noise model.
    // ------------------------------------------------------------------
    public void ExecuteProgrammaticDrop(SlotGeneric targetSlot,
        float motorTime = 0, float motorDistance = 0,
        float motorDistToSlot = 0, float motorHalfDistance = 0,
        float[] motorMinDistances = null)
    {
        EnsureActivated();

        // Find current slot
        if (currentSlot == null)
            currentSlot = findClosestSlot.GetClosestSlot();

        closestSlot = targetSlot;

        // Same slot — no-op
        if (closestSlot == currentSlot)
        {
            transform.position = currentSlot.transform.position;
            currentSlot.SetCardObject(cardObject);
            currentSlot.UpdateManaValue();
            currentSlot.SetFilledInfo(true);
            return;
        }

        // Cannot drop onto SlotNew
        SlotNew slotNewTest = closestSlot.GetComponent<SlotNew>();
        if (slotNewTest != null)
        {
            transform.position = currentSlot.transform.position;
            currentSlot.SetCardObject(cardObject);
            currentSlot.UpdateManaValue();
            currentSlot.SetFilledInfo(true);
            return;
        }

        // Sell slot
        SlotSell slotSellTest = closestSlot.GetComponent<SlotSell>();
        if (slotSellTest != null)
        {
            transform.position = closestSlot.transform.position;
            closestSlot.SetCardObject(cardObject);
            closestSlot.UpdateManaValue();
            closestSlot.SetCardObject(cardObjectNull);
            closestSlot.SetFilledInfo(false);
            currentSlot.SetFilledInfo(false);
            currentSlot.SetCardObject(cardObjectNull);
            currentSlot.UpdateManaValue();
            slotSellTest.SellEffectInitiate();
            Destroy(cardObject.gameObject, 0.3f);
            Destroy(this.gameObject, 0.1f);
            return;
        }

        // Empty slot — move
        if (closestSlot.GetFilledInfo() == false)
        {
            if (recentlyPurchased)
            {
                PerformMotorActionWithParams(motorTime, motorDistance, motorDistToSlot,
                    motorHalfDistance, motorMinDistances);
                PerformBeatAction("empty", closestSlot.slotNumber);
            }
            recentlyPurchased = false;
            transform.position = closestSlot.transform.position;
            currentSlot.SetFilledInfo(false);
            currentSlot.SetCardObject(cardObjectNull);
            currentSlot.UpdateManaValue();
            closestSlot.SetFilledInfo(true);
            closestSlot.SetCardObject(cardObject);
            closestSlot.UpdateManaValue();
            closestSlot.GetComponent<SpriteRenderer>().color = Color.white;
            currentSlot.GetComponent<SpriteRenderer>().color = Color.white;
            currentSlot = closestSlot;
            if (modeMemory == "every action")
                this.memoryCard.ShowAllCardInfo();
            else if (modeMemory == "show one" || modeMemory == "show all")
                this.memoryCard.ShowCardInfo();
            return;
        }

        // Occupied slot — merge
        if (numberOfMerges < maxNumberOfMerges)
        {
            recentlyPurchased = false;
            PerformMotorActionWithParams(motorTime, motorDistance, motorDistToSlot,
                motorHalfDistance, motorMinDistances);
            PerformBeatAction("merge", closestSlot.slotNumber);
            numberOfMerges++;
            transform.position = closestSlot.transform.position;
            closestSlot.GetComponent<SpriteRenderer>().color = Color.white;
            currentSlot.GetComponent<SpriteRenderer>().color = Color.white;
            Card cardOther = closestSlot.GetCardObject();
            if (cardOther == null) { Debug.Log("Agent merge: null card in target slot."); return; }
            CardFrame cardFrameOther = cardOther.GetCardFrame();
            if (cardFrameOther == null) { Debug.Log("Agent merge: null CardFrame."); return; }
            NumberCard numberCardOther = cardFrameOther.numberCard;
            ColorCard colorCardOther = cardFrameOther.colorCard;
            ShapeCard shapeCardOther = cardFrameOther.shapeCard;
            WordCard wordCardOther = cardFrameOther.wordCard;
            if (numberCardOther == null) { Debug.Log("Agent merge: null numberCard."); return; }

            (numberGain, colorGain, shapeGain, wordGain, memoryGain) = AnimateGain(true);
            UpdateDataDict();
            statsCollectorExpanded.UpdateGameStats(dataDictCard, true);

            this.numberCard.MergeNumberCard(numberCardOther.numberSelected);
            this.colorCard.MergeColorCard(colorCardOther.colorSelected, colorCardOther.colorIndexGray);
            this.shapeCard.MergeShapeCard(shapeCardOther.spriteSelectedIndex);
            this.wordCard.MergeWordCard(wordCardOther.wordSelectedList);
            this.memoryCard.MergeMemoryCard(memoryGain);

            closestSlot.SetFilledInfo(true);
            closestSlot.SetCardObject(cardObject);
            closestSlot.UpdateManaValue();

            currentSlot.SetFilledInfo(false);
            currentSlot.SetCardObject(cardObjectNull);
            currentSlot.UpdateManaValue();

            Destroy(cardOther.gameObject, 0.1f);
            Destroy(cardFrameOther.gameObject, 0.1f);

            currentSlot = closestSlot;
            return;
        }
        else
        {
            // Max merges reached — snap back
            transform.position = currentSlot.transform.position;
            currentSlot.SetCardObject(cardObject);
            currentSlot.UpdateManaValue();
            currentSlot.SetFilledInfo(true);
            Debug.Log("Agent: Max number of merges reached.");
        }
    }

    // Motor action with injected parameters (for AI agents)
    private void PerformMotorActionWithParams(float timeSpanned, float distance,
        float distToSlot, float halfDist, float[] minDistSlots)
    {
        if (motorActive)
        {
            // Use injected params if provided, otherwise use defaults
            float t = timeSpanned > 0 ? timeSpanned : 0.5f;
            float d = distance > 0 ? distance : 1f;
            float ds = distToSlot;
            float hd = halfDist;
            float[] ms = minDistSlots != null ? minDistSlots :
                new float[] { 1f, 1f, 1f, 1f, 1f };

            motorGain = this.motorCard.MergeMotorCard(t, d, ds, hd, ms);
            findClosestSlot.ReInitMinDistances();

            if (motorGain == -1f) motorGainSpriteRenderer.sprite = lossSprite;
            else if (motorGain == 0f) motorGainSpriteRenderer.sprite = flatSprite;
            else if (motorGain == 1f) motorGainSpriteRenderer.sprite = gainSprite1;
            else if (motorGain == 2f) motorGainSpriteRenderer.sprite = gainSprite2;
            else if (motorGain == 3f) motorGainSpriteRenderer.sprite = gainSprite3;

            UpdateDataDict();
            statsCollectorExpanded.UpdateGameStats(dataDictCard, false);
            StartCoroutine(ShowMotorGainIcon());
        }
    }

    public void OnMouseDown()
    {
        //Debug.Log("Mouse touch");
        isDragging = true;
        closestComputed = false;
        currentSlot = findClosestSlot.GetClosestSlot();
        startTime = System.DateTime.UtcNow;
        startTimeDrag = System.DateTime.UtcNow;
        clickInitPosition = Camera.main.ScreenToWorldPoint(Input.mousePosition);
    }

    public void OnMouseUp()
    {
        isDragging = false;
    }

    public bool GetIsDragging()
    {
        return isDragging;
    }

    public void SetCardType(float cardTypeInput)
    {
        cardType = cardTypeInput;
    }

    public void SetCardObject(Card cardSet)
    {
        cardObject = cardSet;
    }

    public Card GetCardObject()
    {
        return cardObject;
    }

    //private void OnDestroy()
    //{
    //    Destroy(numberCard.gameObject);
    //    Destroy(colorCard.gameObject);
    //    Destroy(shapeCard.gameObject);
    //    Destroy(wordCard.gameObject);
    //}

}
