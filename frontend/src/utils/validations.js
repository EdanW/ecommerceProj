export const validatePassword = (pwd) => {
    // Rule: 1 Capital, 1 Symbol, 6+ Characters
    const regex = /^(?=.*[A-Z])(?=.*[!@#$&*])(?=.{6,})/;
    return regex.test(pwd);
};

export const validateProfileData = (data) => {
    if (data.age && (data.age <= 18 || data.age >= 60)) {
        return "Please enter a valid age (18-60)";
    }

    if (data.height && (data.height <= 100 || data.height >= 250)) {
        return "Please enter a valid height in cm (100-250)";
    }

    if (data.weight && (data.weight <= 40 || data.weight >= 500)) {
        return "Please enter a valid weight in kg (40-500)";
    }

    if (data.pregnancy_start_date) {
        const date = new Date(data.pregnancy_start_date);
        const today = new Date();
        if (date > today) {
            return "Pregnancy start date cannot be in the future";
        }
    }

    return null;
};