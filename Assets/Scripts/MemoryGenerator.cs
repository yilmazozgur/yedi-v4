using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using BayatGames.SaveGameFree;


public class MemoryGenerator : MonoBehaviour
{
    
    [SerializeField] public float memoryWaitTime = 1f;
    [SerializeField] Card cardPrefab;
    [SerializeField] public Sprite emptySprite;
    [SerializeField] public Sprite fullSprite;

    LevelController levelController;
    CardDrawer cardDrawer;

    bool memoryActivated = false;
    bool memoryModeAdjusted = false;
    string modeMemory = "number_add";
    float cardTypeFromDrawer;
    float cardCostFromDrawer;

    SpriteRenderer spriteRendererSlot1;
    SpriteRenderer spriteRendererSlot2;
    SpriteRenderer spriteRendererSlot3;
    SpriteRenderer spriteRendererSlot4;
    SpriteRenderer spriteRendererSlot5;

    //Card newCardSlot1;
    //Card newCardSlot2;
    //Card newCardSlot3;
    //Card newCardSlot4;
    //Card newCardSlot5;
    //string cardSlot1Json;
    //string cardSlot2Json;
    //string cardSlot3Json;
    //string cardSlot4Json;
    //string cardSlot5Json;

    CardFrame cardFrameSlot1;
    CardFrame cardFrameSlot2;
    CardFrame cardFrameSlot3;
    CardFrame cardFrameSlot4;
    CardFrame cardFrameSlot5;
    string cardFrameSlot1Json;
    string cardFrameSlot2Json;
    string cardFrameSlot3Json;
    string cardFrameSlot4Json;
    string cardFrameSlot5Json;

    SpriteRenderer slot1CardFrameSpriteRenderer;

    Slot1 slot1Object;
    Slot2 slot2Object;
    Slot3 slot3Object;
    Slot4 slot4Object;
    Slot5 slot5Object;


    SlotGeneric slot1GenericObject;
    SlotGeneric slot2GenericObject;
    SlotGeneric slot3GenericObject;
    SlotGeneric slot4GenericObject;
    SlotGeneric slot5GenericObject;

    Transform transformSlot1;
    Transform transformSlot2;
    Transform transformSlot3;
    Transform transformSlot4;
    Transform transformSlot5;

    // Start is called before the first frame update
    void Start()
    {
        cardDrawer = CardDrawer.Instance;
        slot1Object = FindAnyObjectByType<Slot1>();
        slot2Object = FindAnyObjectByType<Slot2>();
        slot3Object = FindAnyObjectByType<Slot3>();
        slot4Object = FindAnyObjectByType<Slot4>();
        slot5Object = FindAnyObjectByType<Slot5>();
       
    }

    public void SetMemoryActivated(bool activationValue)
    {
        memoryActivated = activationValue;
    }

    public void SetMemoryLayout(string modeMemoryValue)
    {
        slot1Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
        slot1Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
        slot2Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
        slot2Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
        slot3Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
        slot3Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
        slot4Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
        slot5Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
        slot5Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
        slot5Object.GetComponent<SpriteRenderer>().sortingOrder = 13;

        //modeMemory = modeMemoryValue;
        //if(memoryModeAdjusted == false)
        // {
        //     memoryModeAdjusted = true;
        //     cardTypeFromDrawer = cardDrawer.GetCardType();
        //     cardCostFromDrawer = cardDrawer.GetCardCost();

        //     if (modeMemory == "number_add")
        //     {
        //         cardDrawer.cardType  = 5f;
        //         cardDrawer.SetCardCost(10f);
        //     }
        //     else if (modeMemory == "color_add")
        //     {
        //         cardDrawer.cardType = 6f;
        //         cardDrawer.SetCardCost(10f);
        //     }
        //     else if (modeMemory == "shape_triangle")
        //     {
        //         cardDrawer.cardType = 7f;
        //         cardDrawer.SetCardCost(10f);
        //     }
        //     else if (modeMemory == "word_verbs")
        //     {
        //         cardDrawer.cardType = 8f;
        //         cardDrawer.SetCardCost(10f);
        //     }

        //     StartCoroutine(InitializeAndHideCards());
        //     //InitializeSlotCards();

        //     cardDrawer.SetCardType(cardTypeFromDrawer);
        //     cardDrawer.SetCardCost(cardCostFromDrawer);
        // }

    }

    //IEnumerator InitializeAndHideCards()
    //{
    //    InitializeSlotCards();
    //    yield return new WaitForSeconds(memoryWaitTime);
    //    slot1Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
    //    slot1Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
    //}

    //public void InitializeSlotCards()
    //{
    //    slot1Object = FindAnyObjectByType<Slot1>();
    //    slot1GenericObject = slot1Object.GetComponent<SlotGeneric>();
    //    transformSlot1 = slot1Object.transform;
        
    //    Card newCardSlot1 = Instantiate(cardPrefab, transformSlot1.position, transformSlot1.rotation) as Card;
    //    slot1GenericObject.SetFilledInfo(true);
    //    slot1GenericObject.SetCardObject(newCardSlot1);
    //    slot1GenericObject.UpdateManaValue();
    //    cardFrameSlot1 = newCardSlot1.cardFrame;
    //    cardFrameSlot1Json = Newtonsoft.Json.JsonConvert.SerializeObject(cardFrameSlot1);
        
    //    //slot1CardFrameSpriteRenderer = cardFrameSlot1.backgroundSpriteRenderer;

    //    slot2Object = FindAnyObjectByType<Slot2>();
    //    slot2GenericObject = slot2Object.GetComponent<SlotGeneric>();
    //    transformSlot2 = slot2Object.transform;
    //    Card newCardSlot2 = Instantiate(cardPrefab, transformSlot2.position, transformSlot2.rotation) as Card;
    //    slot2GenericObject.SetFilledInfo(true);
    //    slot2GenericObject.SetCardObject(newCardSlot2);
    //    slot2GenericObject.UpdateManaValue();
    //    cardFrameSlot2 = newCardSlot2.cardFrame;
    //    cardFrameSlot2Json = Newtonsoft.Json.JsonConvert.SerializeObject(cardFrameSlot2);
        

    //    slot3Object = FindAnyObjectByType<Slot3>();
    //    slot3GenericObject = slot3Object.GetComponent<SlotGeneric>();
    //    transformSlot3 = slot3Object.transform;
    //    Card newCardSlot3 = Instantiate(cardPrefab, transformSlot3.position, transformSlot3.rotation) as Card;
    //    slot3GenericObject.SetFilledInfo(true);
    //    slot3GenericObject.SetCardObject(newCardSlot3);
    //    slot3GenericObject.UpdateManaValue();
    //    cardFrameSlot3 = newCardSlot3.cardFrame;
    //    cardFrameSlot3Json = Newtonsoft.Json.JsonConvert.SerializeObject(cardFrameSlot3);
        

    //    slot4Object = FindAnyObjectByType<Slot4>();
    //    slot4GenericObject = slot4Object.GetComponent<SlotGeneric>();
    //    transformSlot4 = slot4Object.transform;
    //    Card newCardSlot4 = Instantiate(cardPrefab, transformSlot4.position, transformSlot4.rotation) as Card;
    //    slot4GenericObject.SetFilledInfo(true);
    //    slot4GenericObject.SetCardObject(newCardSlot4);
    //    slot4GenericObject.UpdateManaValue();
    //    cardFrameSlot4 = newCardSlot4.cardFrame;
    //    cardFrameSlot4Json = Newtonsoft.Json.JsonConvert.SerializeObject(cardFrameSlot4);
        

    //    slot5Object = FindAnyObjectByType<Slot5>();
    //    slot5GenericObject = slot5Object.GetComponent<SlotGeneric>();
    //    transformSlot5 = slot5Object.transform;
    //    Card newCardSlot5 = Instantiate(cardPrefab, transformSlot5.position, transformSlot5.rotation) as Card;
    //    slot5GenericObject.SetFilledInfo(true);
    //    slot5GenericObject.SetCardObject(newCardSlot5);
    //    slot5GenericObject.UpdateManaValue();
    //    cardFrameSlot5 = newCardSlot5.cardFrame;
    //    cardFrameSlot5Json = Newtonsoft.Json.JsonConvert.SerializeObject(cardFrameSlot5);
        

    //    //Color originalBGColor = slot1CardFrameSpriteRenderer.color;
    //    //originalBGColor.a = 1;
    //    //slot1CardFrameSpriteRenderer.sortingOrder = 11;
    //    //slot1CardFrameSpriteRenderer.color = originalBGColor;
    //}

    //IEnumerator DeployCardsAndHide()
    //{
    //    DeploySlotCards();
    //    yield return new WaitForSeconds(memoryWaitTime);
    //    slot1Object.GetComponent<SpriteRenderer>().sprite = fullSprite;
    //    slot1Object.GetComponent<SpriteRenderer>().sortingOrder = 13;
    //}

    //public void DeploySlotCards()
    //{
        
    //    if (slot1GenericObject.GetFilledInfo() == false)
    //    {
    //        slot1Object.GetComponent<SpriteRenderer>().sprite = emptySprite;
    //        slot1Object.GetComponent<SpriteRenderer>().sortingOrder = 7;

    //        CardFrame cardFrameSlot1Clone = Newtonsoft.Json.JsonConvert.DeserializeObject<CardFrame>(cardFrameSlot1Json);
    //        Card newCardSlot1Clone = Instantiate(cardPrefab, transformSlot1.position, transformSlot1.rotation) as Card;
    //        newCardSlot1Clone.cardFrame = cardFrameSlot1Clone;
    //        slot1GenericObject.SetFilledInfo(true);
    //        slot1GenericObject.SetCardObject(newCardSlot1Clone);
    //        slot1GenericObject.UpdateManaValue();
    //    }
    //    if (slot2GenericObject.GetFilledInfo() == false)
    //    {
    //        CardFrame cardFrameSlot2Clone = Newtonsoft.Json.JsonConvert.DeserializeObject<CardFrame>(cardFrameSlot2Json);
    //        Card newCardSlot2Clone = Instantiate(cardPrefab, transformSlot2.position, transformSlot2.rotation) as Card;
    //        newCardSlot2Clone.cardFrame = cardFrameSlot2Clone;
    //        slot2GenericObject.SetFilledInfo(true);
    //        slot2GenericObject.SetCardObject(newCardSlot2Clone);
    //        slot2GenericObject.UpdateManaValue();
    //    }
    //    if (slot3GenericObject.GetFilledInfo() == false)
    //    {
    //        CardFrame cardFrameSlot3Clone = Newtonsoft.Json.JsonConvert.DeserializeObject<CardFrame>(cardFrameSlot3Json);
    //        Card newCardSlot3Clone = Instantiate(cardPrefab, transformSlot3.position, transformSlot3.rotation) as Card;
    //        newCardSlot3Clone.cardFrame = cardFrameSlot3Clone;
    //        slot3GenericObject.SetFilledInfo(true);
    //        slot3GenericObject.SetCardObject(newCardSlot3Clone);
    //        slot3GenericObject.UpdateManaValue();
    //    }
    //    if (slot4GenericObject.GetFilledInfo() == false)
    //    {
    //        CardFrame cardFrameSlot4Clone = Newtonsoft.Json.JsonConvert.DeserializeObject<CardFrame>(cardFrameSlot4Json);
    //        Card newCardSlot4Clone = Instantiate(cardPrefab, transformSlot4.position, transformSlot4.rotation) as Card;
    //        newCardSlot4Clone.cardFrame = cardFrameSlot4Clone;
    //        slot4GenericObject.SetFilledInfo(true);
    //        slot4GenericObject.SetCardObject(newCardSlot4Clone);
    //        slot4GenericObject.UpdateManaValue();
    //    }
    //    if (slot5GenericObject.GetFilledInfo() == false)
    //    {
    //        CardFrame cardFrameSlot5Clone = Newtonsoft.Json.JsonConvert.DeserializeObject<CardFrame>(cardFrameSlot5Json);
    //        Card newCardSlot5Clone = Instantiate(cardPrefab, transformSlot5.position, transformSlot5.rotation) as Card;
    //        newCardSlot5Clone.cardFrame = cardFrameSlot5Clone;
    //        slot5GenericObject.SetFilledInfo(true);
    //        slot5GenericObject.SetCardObject(newCardSlot5Clone);
    //        slot5GenericObject.UpdateManaValue();
    //    }

    //}
}
