function isString(value) {
    return typeof value === "string" || value instanceof String;
}

function getTypesLength(types) {
    if (isString(types)) {
        return 1;
    }
    else if (Array.isArray(types)) {
        return types.length;
    }
    else {
        return Object.keys(types).length;
    }
}


export {
    isString,
    getTypesLength,
}
