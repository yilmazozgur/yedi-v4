using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class CardDrawer : MonoBehaviour
{
    public static CardDrawer Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    [SerializeField] Card cardPrefab;
    [SerializeField] float cardCost;
    [SerializeField] bool cardSuper;
    [SerializeField] float cardCostSuper;


    public bool haltCardDraw = false;
    bool tutorialPassed = false;
    LevelController levelController;
    TutorialController tutorialController;
    bool firstCardDrawn = false;

    ManaDisplay manaDisplay;
    SuperDisplay superDisplay;
    public float cardType;
    private void Start()
    {
        levelController = LevelController.Instance;
        tutorialController = TutorialController.Instance;
        manaDisplay = ManaDisplay.Instance;
        superDisplay = SuperDisplay.Instance;
        cardType = -1f;
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            DrawCard();
        }
    }

    public void DrawCard()
    {
        if(cardType > 0 && haltCardDraw == false)
        {
            if(firstCardDrawn == false)
            {
                levelController.WorkoutGameUsedUp();
            }
            firstCardDrawn = true;
            SlotNew slotNewObject = FindAnyObjectByType<SlotNew>();
            SlotGeneric slotGenericObject = slotNewObject.GetComponent<SlotGeneric>();
            if (slotGenericObject.GetFilledInfo())
            {
                Debug.Log("Slot New already has a card!");
            }
            else
            {
                if (manaDisplay.HaveEnoughMana(cardCost))
                {
                    if (cardSuper == false)
                    {
                        Transform transformNewSlot = slotNewObject.transform;
                        Card newCard = Instantiate(cardPrefab, transformNewSlot.position, transformNewSlot.rotation) as Card;
                        slotNewObject.DrawEffectInitiate();
                        slotGenericObject.SetFilledInfo(true);
                        slotGenericObject.SetCardObject(newCard);
                        slotGenericObject.UpdateManaValue();
                        levelController.CardDrawn();
                        manaDisplay.SpendMana(cardCost);
                    }
                    else if (cardSuper == true && superDisplay.HaveEnoughSuper(cardType))
                    {
                        Transform transformNewSlot = slotNewObject.transform;
                        Card newCard = Instantiate(cardPrefab, transformNewSlot.position, transformNewSlot.rotation) as Card;
                        slotNewObject.DrawEffectInitiate();
                        slotGenericObject.SetFilledInfo(true);
                        slotGenericObject.SetCardObject(newCard);
                        slotGenericObject.UpdateManaValue();
                        levelController.CardDrawn();
                        manaDisplay.SpendMana(cardCost);
                        superDisplay.SpendSuper(cardType);
                    }

                    if (tutorialController && tutorialController.tutorialInitiated && !tutorialPassed)
                    {
                        tutorialPassed = true;
                        tutorialController.buyCard = true;
                        tutorialController.ContinueFromTutorialPopup();
                    }
                }
                else
                {
                    Debug.Log("Not enough funds!");
                }

            }
        }
        
    }

    public void SetCardType(float cardTypeValue)
    {
        cardType = cardTypeValue;
    }

    public void SetCardCost(float cardCostValue)
    {
        cardCost = cardCostValue;
    }

    public void SetSuperCard(bool superSelection)
    {
        if (superSelection == true)
        {
            superDisplay.PlayAnimation();
        }
        cardSuper = superSelection;
    }

    public bool GetSuperCard()
    {
        return cardSuper;
    }

    public float GetCardType()
    {
        return cardType;
    }

    public float GetCardCost()
    {
        return cardCost;
    }

}
