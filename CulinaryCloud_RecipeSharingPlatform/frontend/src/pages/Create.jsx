
import { useState } from "react";
import Select from "react-select";
import { useNavigate } from "react-router-dom";
import axios from "axios";

function Create(props) {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [steps, setSteps] = useState([
    { 
      id: 1, 
      ingredients: [{ name: "", quantity: "", unit: ""}], 
      description: "", 
      time: { hours: "", minutes: "" } 
    }
  ]);
  const [imageBase64, setImageBase64] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [caption, setCaption] = useState("");
  const [categories, setCategories] = useState([]);
  const [videoUrls, setVideoUrls] = useState([]);
  const [errors, setErrors] = useState({
    title: "",
    categories: "",
    image: "",
    steps: [
      { 
        description: "", 
        ingredients: [{ name: "", quantity: "", unit: "" }],
        time: { hours: "", minutes: "" } 
      }
    ]
  });

  const categoryOptions = [
    { value: "Biryani Varieties", label: "Biryani Varieties" },
    { value: "Nihari Delicacies", label: "Nihari Delicacies" },
    { value: "Karahi Creations", label: "Karahi Creations" },
    { value: "Korma Specialties", label: "Korma Specialties" },
    { value: "Haleem Masterpieces", label: "Haleem Masterpieces" },
    { value: "Kebab Assortments", label: "Kebab Assortments" },
    { value: "Tandoori Treats", label: "Tandoori Treats" },
    { value: "Curry Classics", label: "Curry Classics" },
    { value: "Pulao Dishes", label: "Pulao Dishes" },
    { value: "Daal Delights", label: "Daal Delights" },
    { value: "Chaat Sensations", label: "Chaat Sensations" },
    { value: "Paratha Varieties", label: "Paratha Varieties" },
    { value: "Naan & Flatbreads", label: "Naan & Flatbreads" },
    { value: "Samosa Selections", label: "Samosa Selections" },
    { value: "Pakora & Bhaji", label: "Pakora & Bhaji" },
    { value: "Pickles & Chutneys", label: "Pickles & Chutneys" },
    { value: "Raita & Yogurt Dishes", label: "Raita & Yogurt Dishes" },
    { value: "Saag & Green Vegetable Curries", label: "Saag & Green Vegetable Curries" },
    { value: "Vegetable Curries", label: "Vegetable Curries" },
    { value: "Mughlai Influences", label: "Mughlai Influences" },
    { value: "Street Food Specialties", label: "Street Food Specialties" },
    { value: "Seafood Selections", label: "Seafood Selections" },
    { value: "Traditional Desserts", label: "Traditional Desserts" },
    { value: "Rice Puddings & Kheer", label: "Rice Puddings & Kheer" },
    { value: "Sheer Khurma", label: "Sheer Khurma" },
    { value: "Lassi & Yogurt Drinks", label: "Lassi & Yogurt Drinks" },
    { value: "Chai Varieties", label: "Chai Varieties" },
    { value: "Halwa Creations", label: "Halwa Creations" },
    { value: "Salad & Raita Innovations", label: "Salad & Raita Innovations" },
    { value: "Fusion Desi Snacks", label: "Fusion Desi Snacks" }
  ];

  const addStep = () => {
    setSteps([
      ...steps,
      { 
        id: steps.length + 1, 
        ingredients: [{ name: "", quantity: "", unit: ""}], 
        description: "", 
        time: { hours: "", minutes: "" } 
      }
    ]);
    setErrors(prevErrors => ({
      ...prevErrors,
      steps: [
        ...prevErrors.steps,
        {
          description: "",
          ingredients: [{ name: "", quantity: "", unit: "" }],
          time: { hours: "", minutes: "" }
        }
      ]
    }));
  };

  const updateIngredient = (stepIndex, ingredientIndex, value, field) => {
    const newSteps = [...steps];
    newSteps[stepIndex].ingredients[ingredientIndex][field] = value;
    setSteps(newSteps);
    setErrors(prevErrors => {
      const newErrors = { ...prevErrors };
      newErrors.steps[stepIndex].ingredients[ingredientIndex][field] = "";
      return newErrors;
    });
  };
  
  const addIngredient = (stepIndex) => {
    const newSteps = [...steps];
    newSteps[stepIndex].ingredients.push({ name: "", quantity: "", unit: "" });
    setSteps(newSteps);
    setErrors(prevErrors => {
      const newErrors = { ...prevErrors };
      newErrors.steps[stepIndex].ingredients.push({ name: "", quantity: "", unit: "" });
      return newErrors;
    });
  };
  
  const removeIngredient = (stepIndex) => {
    const newSteps = [...steps];
    if (newSteps[stepIndex].ingredients.length > 1) {
      newSteps[stepIndex].ingredients.pop();
      setSteps(newSteps);
      setErrors(prevErrors => {
        const newErrors = { ...prevErrors };
        if (newErrors.steps[stepIndex].ingredients.length > 1) {
          newErrors.steps[stepIndex].ingredients.pop();
        }
        return newErrors;
      });
    }
  };

  const deleteStep = (stepIndex) => {
    if (stepIndex > 0) {
      setSteps(steps.filter((_, index) => index !== stepIndex));
      setErrors(prevErrors => ({
        ...prevErrors,
        steps: prevErrors.steps.filter((_, index) => index !== stepIndex)
      }));
    }
  };

  const updateStepField = (stepIndex, field, value) => {
    const newSteps = [...steps];
    if (field === "description") {
      newSteps[stepIndex].description = value;
      setErrors(prevErrors => {
        const newErrors = { ...prevErrors };
        newErrors.steps[stepIndex].description = "";
        return newErrors;
      });
    } else if (field === "hours" || field === "minutes") {
      newSteps[stepIndex].time[field] = value;
    }
    setSteps(newSteps);
  };

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImageBase64(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleVideoUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("video", file);

    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/recipes/upload-video`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            "x-auth-token": localStorage.getItem("token"),
          },
        }
      );
      setVideoUrls((prev) => [...prev, res.data.videoUrl]);
      alert("Video uploaded successfully!");
    } catch (err) {
      console.error("Video upload failed:", err);
      alert("Video upload failed.");
    }
  };

  const handleSubmit = async () => {
    let hasErrors = false;
    const newErrors = {
      title: title ? "" : "*Required",
      categories: categories.length > 0 ? "" : "*At least one category is required",
      image: imageFile ? "" : "*Image is required",
      steps: steps.map((step) => {
        // Validate time
        const hours = step.time.hours;
        let hoursError = "";
        if (hours !== "") {
          const hoursNum = parseFloat(hours);
          if (isNaN(hoursNum)) {
            hoursError = "Invalid number";
          } else if (hoursNum < 0) {
            hoursError = "Must be ≥0";
          }
        }

        const minutes = step.time.minutes;
        let minutesError = "";
        if (minutes !== "") {
          const minutesNum = parseFloat(minutes);
          if (isNaN(minutesNum)) {
            minutesError = "Invalid number";
          } else if (minutesNum < 0) {
            minutesError = "Must be ≥0";
          } else if (minutesNum >= 60) {
            minutesError = "Must be <60";
          }
        }

        // Validate ingredients
        const ingredientsErrors = step.ingredients.map((ingredient) => {
          let quantityError = "";
          if (ingredient.quantity === "") {
            quantityError = "*Required";
          } else {
            const qty = parseFloat(ingredient.quantity);
            if (isNaN(qty)) {
              quantityError = "Invalid number";
            } else if (qty <= 0) {
              quantityError = "Must be >0";
            }
          }

          return {
            name: ingredient.name ? "" : "*Required",
            quantity: quantityError,
            unit: ingredient.unit ? "" : "*Required"
          };
        });

        return {
          description: step.description ? "" : "*Required",
          ingredients: ingredientsErrors,
          time: {
            hours: hoursError,
            minutes: minutesError
          }
        };
      })
    };

    // Check for any errors
    if (newErrors.title) hasErrors = true;
    if (newErrors.categories) hasErrors = true;
    if (newErrors.image) hasErrors = true; 
    newErrors.steps.forEach(stepError => {
      if (stepError.description) hasErrors = true;
      stepError.ingredients.forEach(ingError => {
        if (ingError.name || ingError.quantity || ingError.unit) hasErrors = true;
      });
      if (stepError.time.hours || stepError.time.minutes) hasErrors = true;
    });

    setErrors(newErrors);

    if (hasErrors) {
      return;
    }

    const token = localStorage.getItem("token");
    const formData = new FormData();
    formData.append("title", title);
    formData.append("steps", JSON.stringify(steps));
    formData.append("caption", caption);
    formData.append("categories", JSON.stringify(categories));
    formData.append("videoUrls", JSON.stringify(videoUrls));

    if (imageFile) {
      formData.append("image", imageFile);
    }

    try {
      console.log("Sending token:", token);
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/recipes`, {
        method: "POST",
        headers: {
          "x-auth-token": token
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Recipe submitted:", data);
        navigate("/home");  
      } else {
        const err = await response.json();
        // alert(err.msg || "Failed to post recipe");
      }
    } catch (err) {
      console.error("Submission error:", err);
    }
  };

  return (
    <div className="post-recipe">
      <div className="recipe-title-container">
        <input
          type="text"
          placeholder={errors.title || "Recipe Title"}
          className={`recipe-title ${errors.title ? "input-error" : ""}`}
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setErrors(prevErrors => ({ ...prevErrors, title: "" }));
          }}
        />
      </div>
      {steps.map((step, stepIndex) => (
        <div key={step.id}>
          <h3 className="step-number">Step {stepIndex + 1}</h3>
          <h5 className="step-titles">Ingredients</h5>
          <div className="ingredients">
            {step.ingredients.map((ingredient, ingredientIndex) => (
              <div key={ingredientIndex} className="single-ingredient">
                <input
                  type="text"
                  placeholder={errors.steps[stepIndex].ingredients[ingredientIndex].name || `Ingredient ${ingredientIndex + 1}`}
                  className={`input-ingredient-field ${errors.steps[stepIndex].ingredients[ingredientIndex].name ? "input-error" : ""}`}
                  value={ingredient.name}
                  onChange={(e) =>
                    updateIngredient(stepIndex, ingredientIndex, e.target.value, "name")
                  }
                />
                <input
                  type="text"
                  placeholder={errors.steps[stepIndex].ingredients[ingredientIndex].quantity || "Quantity"}
                  className={`input-quantity-field ${errors.steps[stepIndex].ingredients[ingredientIndex].quantity ? "input-error" : ""}`}
                  value={ingredient.quantity}
                  onChange={(e) =>
                    updateIngredient(stepIndex, ingredientIndex, e.target.value, "quantity")
                  }
                />
                <select
                  className={`input-unit-field ${errors.steps[stepIndex].ingredients[ingredientIndex].unit ? "input-error" : ""}`}
                  value={ingredient.unit}
                  onChange={(e) =>
                    updateIngredient(stepIndex, ingredientIndex, e.target.value, "unit")
                  }
                >
                  <option value="">Unit</option>
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="ml">ml</option>
                  <option value="l">l</option>
                  <option value="tsp">tsp</option>
                  <option value="tbsp">tbsp</option>
                  <option value="cup">cup</option>
                  <option value="pinch">pinch</option>
                  <option value="slice">slice</option>
                  <option value="piece">piece</option>
                </select>
                {ingredientIndex === step.ingredients.length - 1 && (
                  <div className="ingredient-btns">
                    <button
                      onClick={() => addIngredient(stepIndex)}
                      className="add-ingredients"
                    >
                      Add
                    </button>
                    <button
                      className="remove-ingredients"
                      onClick={() => removeIngredient(stepIndex)}
                    >
                      Remove
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          <h5 className="step-titles">Description</h5>
          <input
            type="text"
            placeholder={errors.steps[stepIndex].description || "Explanation of this step"}
            className={`input-description-field ${errors.steps[stepIndex].description ? "input-error" : ""}`}
            value={step.description}
            onChange={(e) =>
              updateStepField(stepIndex, "description", e.target.value)
            }
          />
          <h5 className="step-titles">Time (if applicable)</h5>
          <div className="time-container">
            <input
              type="number"
              placeholder={errors.steps[stepIndex].time.hours || "hours"}
              className={`time-field1 ${errors.steps[stepIndex].time.hours ? "input-error" : ""}`}
              value={step.time.hours}
              onChange={(e) =>
                updateStepField(stepIndex, "hours", e.target.value)
              }
            />
            <input
              type="number"
              placeholder={errors.steps[stepIndex].time.minutes || "mins"}
              className={`time-field2 ${errors.steps[stepIndex].time.minutes ? "input-error" : ""}`}
              value={step.time.minutes}
              onChange={(e) =>
                updateStepField(stepIndex, "minutes", e.target.value)
              }
            />
          </div>
        </div>
      ))}

      <button className="delete-step" onClick={() => deleteStep(steps.length - 1)}>
        Delete Step
      </button>
      <div className="add-step">
        <button className="step-btn" onClick={addStep}>+</button>
        <p className="step-txt">Add Step</p>
      </div>

      <div className="image" onClick={() => document.getElementById("imageUpload").click()}>
        <i className="fa-solid fa-paperclip" style={{ cursor: "pointer" }}></i>
        <p className="image-txt">Upload Image</p>
      </div>
      <input
        type="file"
        id="imageUpload"
        accept="image/*"
        style={{ display: "none" }}
        onChange={handleImageUpload}
      />
      {imageBase64 && (
        <img src={imageBase64} alt="Uploaded" className="uploaded-image" />
      )}

      <input
        type="text"
        placeholder="Caption (optional)"
        className="caption-field"
        value={caption}
        onChange={(e) => setCaption(e.target.value)}
      />

      <Select
        isMulti
        name="categories"
        options={categoryOptions}
        className={`category-dropdown ${errors.categories ? "input-error" : ""}`}
        classNamePrefix="select"
        value={categoryOptions.filter((option) => categories.includes(option.value))}
        onChange={(selected) => {
          if (selected.length <= 3) {
            setCategories(selected.map((s) => s.value));
            setErrors(prevErrors => ({ ...prevErrors, categories: "" }));
          }
        }}
        placeholder={errors.categories || "Select up to 3 categories"}
        styles={{
          control: (base, state) => ({
            ...base,
            backgroundColor: "#fff",
            borderColor: state.isFocused ? "#6CBF84" : errors.categories ? "red" : "#ccc",
            boxShadow: state.isFocused ? "0 0 0 2px rgba(108, 191, 132, 0.3)" : "none",
            borderRadius: "6px",
            minHeight: "48px",
            fontSize: "0.95rem",
            transition: "all 0.2s ease",
          }),
          placeholder: (base) => ({
            ...base,
            color: errors.categories ? "red" : "#aaa",
          }),
          multiValue: (base) => ({
            ...base,
            backgroundColor: "#6CBF84",
            color: "white",
            borderRadius: "4px",
            padding: "0 4px",
          }),
          multiValueLabel: (base) => ({
            ...base,
            color: "white",
            fontWeight: "500",
          }),
          option: (base, state) => ({
            ...base,
            backgroundColor: state.isSelected
              ? "#2E7D32"
              : state.isFocused
              ? "#F1F8E9"
              : "white",
            color: state.isSelected ? "white" : "#333",
            padding: "10px",
          }),
        }}
      />

      <div className="video-container">
        <h5 className="step-titles">Upload a Video</h5>
        <input type="file" accept="video/*" onChange={handleVideoUpload} className="choose-video"/>
      </div>

      {videoUrls.map((url, index) => (
        <video key={index} controls width="100%" style={{ marginTop: "10px" }}>
          <source src={url} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      ))}
      <button className="submit-part" onClick={handleSubmit}>
        Submit
      </button>

      <style jsx>{`
        .input-error {
          border: 1px solid red;
        }
        .input-error::placeholder {
          color: red;
        }
      `}</style>
    </div>
  );
}

export default Create;